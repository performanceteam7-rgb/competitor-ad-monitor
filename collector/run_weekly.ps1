# 주 1회 자동 갱신: Meta 광고 수집 → data.js 재생성 → Vercel 재배포
# Windows 작업 스케줄러에 등록해 사용. (사용자 Chrome이 실행 중이어야 함 — Meta 라이브러리는 로그인 불필요)
$ErrorActionPreference = "Continue"
$Base    = "C:\Users\MADUP\competitor-ad-monitor"
$BH      = "C:\Users\MADUP\.local\bin\browser-harness.exe"
$LogDir  = Join-Path $Base "collector\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp   = Get-Date -Format "yyyy-MM-dd"
$Log     = Join-Path $LogDir "$Stamp.log"

"=== 주간 수집 시작 $(Get-Date) ===" | Tee-Object -FilePath $Log

# 1) 수집 (실행일 날짜 주입)
$env:PYTHONIOENCODING = "utf-8"
$env:BH_TODAY = $Stamp
cmd /c "`"$BH`" < `"$Base\collector\run_collect.py`"" 2>&1 | Tee-Object -FilePath $Log -Append

# 2) 재배포 (인증 토큰은 1회 로그인 후 저장됨)
Set-Location $Base
cmd /c "npx --yes vercel --prod --yes" 2>&1 | Tee-Object -FilePath $Log -Append

"=== 완료 $(Get-Date) ===" | Tee-Object -FilePath $Log -Append
