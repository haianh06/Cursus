@echo off
REM Cai dat va kiem tra AI Log Bridge — mot lenh duy nhat.
REM
REM   tools\ai-log-extension\setup.cmd              cai + kiem tra
REM   tools\ai-log-extension\setup.cmd --check      chi kiem tra
REM   tools\ai-log-extension\setup.cmd --server     kiem tra ca grading server
REM
REM Chay duoc bang cach nhay doi chuot. Wrapper chi lo tim Python — moi logic
REM nam trong setup.py de Windows va macOS/Linux dung chung mot duong code.

setlocal
set "HERE=%~dp0"
set "REPO=%HERE%..\.."

if exist "%REPO%\.venv\Scripts\python.exe" (
  "%REPO%\.venv\Scripts\python.exe" "%HERE%setup.py" %*
  goto :done
)

where py >nul 2>nul && (
  py -3 "%HERE%setup.py" %*
  goto :done
)

where python >nul 2>nul && (
  python "%HERE%setup.py" %*
  goto :done
)

echo Khong tim thay Python. Cai Python roi chay lai.
exit /b 1

:done
set RC=%ERRORLEVEL%
REM Nhay doi chuot thi cua so dong ngay — giu lai de doc ket qua.
if "%~1"=="" pause
exit /b %RC%
