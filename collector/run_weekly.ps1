# 주 1회 자동 갱신: Meta 광고 수집 → data.js 재생성 → Vercel 재배포
# Windows 작업 스케줄러에 등록해 사용. (사용자 Chrome이 실행 중이어야 함 — Meta 라이브러리는 로그인 불필요)
#
# self-verifying: 각 단계 성공 여부를 실제로 검증하고, 실패 시 log에 [FAIL] 남기고 exit 1.
# (과거엔 ErrorActionPreference=Continue 라 내부 단계가 죽어도 태스크가 성공(0)으로 표시돼
#  한 달간 갱신이 멈춘 걸 아무도 몰랐음 → 이제 실패하면 LastTaskResult != 0 으로 잡힘)
#
# 수집기 호출: uv 트램폴린(.local\bin\browser-harness.exe)은 스케줄러 환경에서
#   'uv trampoline failed to canonicalize script path' 로 깨짐 → venv Python 직접 호출로 우회.

$ErrorActionPreference = "Continue"
$Base    = "C:\Users\MADUP\competitor-ad-monitor"
# 수집기 실행: venv Python 직접 호출(트램폴린 우회). 없으면 트램폴린으로 fallback.
$VPY     = "C:\Users\MADUP\AppData\Roaming\uv\tools\browser-harness\Scripts\python.exe"
$BH      = "C:\Users\MADUP\.local\bin\browser-harness.exe"
$LogDir  = Join-Path $Base "collector\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp   = Get-Date -Format "yyyy-MM-dd"
$Log     = Join-Path $LogDir "$Stamp.log"
$DataJs  = Join-Path $Base "data.js"
# lastUpdated 값은 "YYYY-MM-DD 09:00" — 신규 수집에만 나타나는 고유 패턴(개별 광고 날짜엔 시각 없음)
$Marker  = $Stamp + ' 09:00'
$RunPy   = Join-Path $Base "collector\run_collect.py"

function Log($msg) { "$msg" | Tee-Object -FilePath $Log -Append }

"=== 주간 수집 시작 $(Get-Date) ===" | Tee-Object -FilePath $Log   # -Append 없이 새 로그 시작

# 0) 수집기 커맨드 결정 (venv python 우선, 없으면 트램폴린)
$env:PYTHONIOENCODING = "utf-8"
$env:BH_TODAY = $Stamp
if (Test-Path $VPY) {
    $CollectCmd = "`"$VPY`" -c `"from browser_harness.run import main; main()`" < `"$RunPy`""
    Log "[INFO] 수집기: venv python 직접 호출 (트램폴린 우회)"
} elseif (Test-Path $BH) {
    $CollectCmd = "`"$BH`" < `"$RunPy`""
    Log "[INFO] 수집기: 트램폴린 fallback"
} else {
    Log "[FAIL] browser-harness 실행 파일 없음 (venv/트램폴린 모두 없음) — uv tool 재설치 필요"
    exit 1
}

# 1) 수집
cmd /c $CollectCmd 2>&1 | Tee-Object -FilePath $Log -Append

# 1-검증) data.js 가 실제로 오늘 날짜로 갱신됐는지 확인
if (-not (Test-Path $DataJs)) {
    Log "[FAIL] data.js 없음 — 수집 실패"
    exit 1
}
$dataContent = Get-Content $DataJs -Raw
if (-not ($dataContent -match [regex]::Escape($Marker))) {
    Log "[FAIL] data.js 가 오늘($Stamp)로 갱신 안 됨 — 수집기(browser-harness/Chrome) 확인 필요"
    exit 1
}
Log "[OK] 수집 검증 통과 — data.js lastUpdated=$Marker"

# 2) 재배포 (인증 토큰은 1회 로그인 후 저장됨. 토큰 만료 시 여기서 실패로 잡힘)
Set-Location $Base
$deployOut = cmd /c "npx --yes vercel --prod --yes" 2>&1
$deployOut | Tee-Object -FilePath $Log -Append
$deployText = $deployOut | Out-String
if ($deployText -match 'not valid' -or $deployText -match 'vercel login' -or $deployText -match 'Error:') {
    Log "[FAIL] Vercel 배포 실패 — 토큰 만료 가능성. 'vercel login' 재실행 또는 VERCEL_TOKEN 설정 필요"
    exit 1
}

# 2-검증) 라이브 사이트가 오늘 날짜를 서빙하는지 확인
Start-Sleep -Seconds 5
$cb = Get-Random
try {
    $live = Invoke-WebRequest -Uri "https://competitor-ad-monitor.vercel.app/data.js?cb=$cb" -UseBasicParsing -TimeoutSec 30
    if ($live.Content -match [regex]::Escape($Marker)) {
        Log "[OK] 라이브 사이트 검증 통과 — $Stamp 서빙 중"
    } else {
        Log "[WARN] 배포는 됐으나 라이브가 아직 $Stamp 반영 안 됨 (CDN 캐시 지연 가능)"
    }
} catch {
    Log "[WARN] 라이브 확인 실패(네트워크): $_"
}

Log "=== 완료(SUCCESS) $(Get-Date) ==="
exit 0
