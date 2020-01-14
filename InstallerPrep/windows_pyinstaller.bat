cd ..

set PATH=%PATH%;C:\Program Files (x86)\Python;C:\Program Files (x86)\Python\Scripts
set TEMPDIR=%TEMP%\EDProxyBuild
set OUTPUTEXE=.\Release\EDProxy.exe

echo CD : %CD%

if exist "%TEMPDIR%" (
	rmdir /Q /S "%TEMPDIR%"
)
mkdir "%TEMPDIR%" || goto :error

if exist "%OUTPUTEXE%" (
	del /Q "%OUTPUTEXE%" || goto :error
)

pyinstaller --clean --distpath .\Release --workpath "%TEMPDIR%" -y -w --icon=edicon.ico --onefile -n EDProxy edproxy.py || goto :error

"C:\Program Files (x86)\Windows Kits\10\App Certification Kit\signtool" sign /n "JK CUSTOM CODING LTD" /v /d "EDProxy" /du https://www.fsmissioneditor.com/ /tr http://timestamp.sectigo.com/rfc3161 .\Release\EDProxy.exe || goto :error

rmdir /Q /S "%TEMPDIR%"

exit /b 0
goto :EOF

:error
echo Installation script failed RC %ERRORCODE%
exit /b %ERRORCODE%
