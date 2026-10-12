@echo off
setlocal EnableExtensions
title Build Leftover's
cd /d "%~dp0"
echo.
echo This builds:
echo   dist\Leftover's.exe
echo   dist\Leftover's Setup.exe
echo.
set "PY="
where py >nul 2>&1
if not errorlevel 1 (
  for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PY=%%I"
)
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%I in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PY=%%I"
  )
)
if not defined PY (
  for %%V in (313 312 311 310) do (
    if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
    if not defined PY if exist "%ProgramFiles%\Python%%V\python.exe" set "PY=%ProgramFiles%\Python%%V\python.exe"
  )
)
if not defined PY (
  echo Python was not found. Paste the full path to python.exe.
  set /p PY=Full path to python.exe: 
)
if not exist "%PY%" (
  echo That python.exe does not exist:
  echo   %PY%
  pause
  exit /b 1
)
echo Using Python:
echo   %PY%
echo.
if not exist "leftover_drive_scan.py" (
  echo Missing leftover_drive_scan.py
  pause
  exit /b 1
)
if not exist "setup_wizard.py" (
  echo Missing setup_wizard.py
  pause
  exit /b 1
)
echo Writing leftover_icon_32.ico
if exist leftover_icon.b64 del /q leftover_icon.b64
>>leftover_icon.b64 echo AAABAAEAICAAAAEAIACoEAAAFgAAACgAAAAgAAAAQAAAAAEAIAAAAAAAgBAAAAAAAAAAAAAAAAAAAAAAAAD+/v7///////////+lpaT/SkhH/yUjIv8iIB//
>>leftover_icon.b64 echo IiAf/yIgH/8iIB//IiAf/yIgH/8iIB//IiAf/yIgH/8iIB//IiAf/yIgH/8iIB//IiAf/yIgH/8iIB//IiAf/yIgH/8iIB//IiAf/yUjIv9JSEf/paWk////
>>leftover_icon.b64 echo /////////v7+//7+/v/z8/P/YmFg/xYUE/8cGhr/IyEg/yMhIf8jISD/IyEg/yMhIP8jISD/IyEg/yMhIP8jISD/IyEg/yMhIP8jISD/IyEg/yMhIP8jISD/
>>leftover_icon.b64 echo IyEg/yMhIP8jISD/IyEg/yMhIP8jISD/IyEg/xwaGf8WFBP/YmFg//Tz8//+/v7//f39/2RjYv8NCwr/KCYl/yUjI/8kIiH/JCIh/yQiIf8kIiH/JCIh/yMh
>>leftover_icon.b64 echo If8kIiH/IyEh/yQiIf8jISH/IyEh/yMhIf8jISH/JCIh/yQiIf8jISH/IyEh/yQiIf8kIiH/JCIh/yQiIf8jISH/JSMj/ygmJf8NCwr/ZGNi//39/f+qqan/
>>leftover_icon.b64 echo FxQT/yknJv8kIiL/JCIi/yQiIv8kIiL/JCIi/yQiIv8kIiL/JCIh/yQiIv8lIyL/JSMi/yQiIf8kIiH/JCIi/yQiIf8kIiL/JSMi/yQiIf8kIiH/JCIi/yQi
>>leftover_icon.b64 echo Iv8kIiH/JCIi/yQiIv8kIiL/JSMi/ygmJv8WFBT/qqmp/0pJSP8eHBv/JiQk/yUjIv8lIyL/JCIi/yUjIv8lIyL/JSMi/yUjIv8lIyL/JSMi/yUjIv8lIyL/
>>leftover_icon.b64 echo JSMi/yQiIv8kIiL/JSMi/yUjIv8mJCP/JyQl/yUjI/8lIyL/JSMi/yUjIv8kIiL/JSMi/yUjIv8lIyL/JiQj/x4cG/9KSEf/JyUl/yUjI/8lIyP/JSMj/yUj
>>leftover_icon.b64 echo I/8lIyP/JSMj/yUjI/8lIyP/JSMj/yUjIv8lIyP/JSMi/yUjI/8lIyP/JSMj/yUjI/8lIyL/JiQl/yIhHf8cHRT/JCIh/yYkJf8lIyP/JSMj/yUjI/8lIyP/
>>leftover_icon.b64 echo JSMj/yUjI/8lIyP/JSMi/yclJf8mJCT/JiQk/yYkJP8mJCT/JiQk/yYkJP8mJCT/JiQk/yYkJP8mJCT/KCYm/yclJf8mJCT/JyUk/yYkJP8mJCT/JiQk/ygl
>>leftover_icon.b64 echo KP8gIBn/ODBC/1xHgf8rJyz/IyIe/yglJ/8mJCT/JiQk/yYkJP8mJCT/JiQk/yYkJP8mJCT/JiQj/yclJf8nJSX/JyUl/yclJf8nJSX/JyUl/yclJf8nJSX/
>>leftover_icon.b64 echo JyUl/yclJf8fHR3/IiAg/yknJv8nJSX/JyUl/yclJP8pJin/ICEZ/zkxRf+Qatz/pHf//35evv8qJyr/JCMf/ykmKP8nJSX/JyUl/yclJf8nJSX/JyUk/ycl
>>leftover_icon.b64 echo Jf8nJSX/KCYm/ygmJv8oJiX/JyUl/ygmJf8nJSX/JyUl/ygmJf8oJib/IiAf/1xZWP9IRkX/Hh0c/yooJ/8nJSX/Kicp/yEhGf86MkX/k2zg/51y8f+TbeL/
>>leftover_icon.b64 echo nnP2/4Fgwv8rKCv/JSQg/yonKP8oJiX/KCYl/ygmJf8oJiX/KCYl/yclJf8oJyb/KScn/ygmJv8oJib/KCYm/ygmJv8oJib/Kigo/x4cHP9gXl3/y8fG/6Sg
>>leftover_icon.b64 echo nv9GREP/IB4e/y0qLP8iIhv/OzNG/5Ru4f+edPL/mHDo/5px6/+Xb+b/oHX3/4Niw/8sKSz/JSQg/yknKP8oJib/KCYm/ygnJ/8oJib/KCYm/yknJ/8pJyf/
>>leftover_icon.b64 echo KScn/yknJ/8pJyf/KScn/yknJ/8qKCj/JSMj/z89Pf+5trX/xcLB/6ejof9JR0f/GhsU/z01SP+Wb+L/oHbz/5py6P+cc+z/m3Ps/5xz7f+Zcej/o3f5/4Rj
>>leftover_icon.b64 echo w/8uKzD/KCYl/yooKP8pJyf/KScn/yknJ/8pJyf/Kigo/yooKP8qKCj/Kigo/yooKP8qKCj/Kigo/yooKP8sKir/IR8f/zs6Of+7ubj/y8fH/6ajoP9aUmL/
>>leftover_icon.b64 echo kmze/6R59/+dc+//n3P0/5908v+fdu//nnXt/5517/+acuf/qXz//25WnP8iIxr/LCos/yooKP8qKCj/Kigo/yooKP8rKSn/Kykp/yspKf8rKSn/Kykp/ysp
>>leftover_icon.b64 echo Kf8rKSn/Kykp/yspKf8uLCz/IiAg/z48Pf+6uLT/y8q+/7CnuP+ec/H/nHPu/5t52/+cfdP/mnja/5xz7f+gdvT/n3ft/6B38P+levj/UUNq/yUlH/8sKiv/
>>leftover_icon.b64 echo Kykp/yspKf8rKSn/Kykp/yspKf8sKir/LCop/ywqKf8rKSn/Kykp/yspKf8rKSn/LCop/yspKf8xLjD/GxwU/1VMYP/KvN7/qKaf/5uLs/+mmLf/qKag/6Gg
>>leftover_icon.b64 echo mP+no6D/o5iu/5t62f+jefj/p336/1dHc/8kJBv/LSor/yspKf8rKSn/Kykp/yspKf8rKSn/LCoq/ywqKv8sKir/LCoq/ywqKv8sKir/LCoq/ywqKv8sKir/
>>leftover_icon.b64 echo Lywu/yQlHv9BOUz/mXPi/6F0+f+kjcr/trem/5GPiv9PTUz/Pzw9/1BNTv+NjIT/qKSk/5583f9ZR3j/IyQa/y4rLf8sKir/LCoq/ywqKv8sKir/LCop/ywq
>>leftover_icon.b64 echo Kv8tKyv/LSsq/y0rKv8tKyv/LSsr/y0rK/8tKyv/LSsq/y8sLv8lJh//PzhL/5556P+rg/v/oXjx/7Slyv+dm5X/LCks/yUjI/8qKCj/JCIi/yooKf+ZlpP/
>>leftover_icon.b64 echo kIyN/yMiH/8vLC3/LSsr/y0rK/8tKyr/LSsq/y0rK/8sKir/LCoq/y0rK/8uLCv/Liwr/y4sK/8tKyv/Liws/y0rK/8wLS7/JyYi/0A4Sv+ge+j/q4P6/6V9
>>leftover_icon.b64 echo 8/+lger/xcHC/15cWv8jISL/MjAw/y4sLP8xLy//IyEh/1tYWP+0sa//OTc3/yooKP8uLCz/LSsr/y0rK/8uLCv/Liws/y4sLP8tKyv/Liws/y4sLP8uLCz/
>>leftover_icon.b64 echo Liws/y4sLP8uLCz/MC4v/yclJf8+Oj7/on3o/66E/v+ogfL/qYD5/6qJ6v/JxcT/TkxL/yknJv8vLS3/Liws/y8tLf8pJyf/S0lJ/766uf9EQkH/KScn/y8t
>>leftover_icon.b64 echo Lf8uLCv/LSsr/y4sLP8uLCz/Liws/y4sK/8vLS3/Ly0t/y8tLf8vLS3/Ly0t/zAuLv8nJiT/Pz84/6Kfmf+wnsr/qX/4/6uE+P+rg/j/qYTw/9PO1P9ta2n/
>>leftover_icon.b64 echo IR8f/zUzMv8wLi7/NDIy/yEfH/9qaGf/wr++/zY0M/8sKir/Ly0t/y4sLP8vLSz/Ly0s/y8tLf8vLSz/Liws/zAuLf8vLS3/Ly0t/y8tLf8wLi//LCwo/z42
>>leftover_icon.b64 echo Sf+hiMv/urez/7O0pP+xoMr/rIL7/66G+f+pf/n/xbTg/8TEuP86ODr/Hx0d/yclJf8gHh7/NzU1/8fExP+Rjo7/JCIi/zEvL/8vLS3/Ly0t/y8tLf8vLS3/
>>leftover_icon.b64 echo Ly0t/y8tLf8vLS3/MC4u/zAuLv8wLi7/MC4u/zIvMf8lJh3/gGas/7yM//+tkd7/v7y3/7+/sv+3ptH/roT8/6+G/P+th/T/08nc/9LQy/9/fHz/YV5e/3t5
>>leftover_icon.b64 echo ef/Qzcz/u7i3/zY0NP8tKyv/MC4u/zAuLv8wLi7/MC4u/zAuLv8wLi7/MC4u/zAuLv8xLy//MC4u/zAuLv8wLi7/Mi8w/ywrJ/9MQlr/sIjz/7OH//+0l+b/
>>leftover_icon.b64 echo x8TB/8nIvf+9q9f/roX8/7KH/v+xivf/nJag/8zKx//X1NP/zsvK/5COjf81MzP/LCoq/zEvL/8wLi7/MC4u/zAuLv8wLi7/MC4u/zAuLv8xLy7/MS8u/zEv
>>leftover_icon.b64 echo L/8xLy//MS8v/zEvL/8xLy//MzAy/ygpIf9PRF//sov1/7OI//+4nOn/0MzK/9HRxf/Csdz/uZD9/2JRff8gIBz/MjAw/zw6Ov8xLy//JCMi/y8tLf8yMDD/
>>leftover_icon.b64 echo MC4u/zEvL/8xLy//MS8v/zEvL/8xLy//MS8v/zEvL/8xLy//MjAw/zIwMP8yMDD/MjAw/zIwMP8yMC//NDI0/ykpIf9PRWD/s471/7SK//+5ner/1tPQ/9/e
>>leftover_icon.b64 echo 2P9qY3P/JiUh/zU0M/8wLi//LSwr/zAuLv80MjL/MzEx/zIwMP8yMDD/MjAw/zIwMP8yMDD/MjAw/zIwMP8yMC//MjAv/zIwL/8zMTH/MzEw/zMxMP8zMTD/
>>leftover_icon.b64 echo MjAw/zIwMP8zMTD/NTI0/ykqIv9RRmH/to/1/7uP///Hqvn/dnRx/yclIv81MzP/MjAw/zMxMP8zMTH/MzEx/zIwMP8yMDD/MjAw/zIwMP8yMDD/MzEw/zMx
>>leftover_icon.b64 echo MP8yMDD/MjAw/zIwMP8yMDD/MzEw/zMxMf80MjH/MzEx/zMxMf8zMTH/MzEx/zMxMf8zMTD/NjM1/ykqIv9SR2L/o4PQ/2VTg/8nJiP/NTI0/zMxMf8zMTH/
>>leftover_icon.b64 echo MzEx/zMxMf8zMTH/MzEx/zMxMf8zMTH/MzEx/zMxMf8zMTH/MzEx/zMxMf8zMTH/MzEx/zMxMf8zMTH/NjMz/zQyMf80MjH/MzEx/zMxMf80MjH/NDEx/zQy
>>leftover_icon.b64 echo Mf8zMTH/NTM0/y8uKv8uLiv/Li4o/zUzMv8zMTH/MzEx/zMxMf8zMTH/MzEx/zQyMv80MjL/NDIy/zQyMf8zMTH/NDIy/zMxMf8zMTH/MzEx/zMxMf80MjH/
>>leftover_icon.b64 echo MzEx/zUzM/9XVlX/Liws/zY0NP80MjL/NDIy/zQyMv80MjL/NDIy/zQyMv80MjL/NTM0/zUzM/81MzT/NDIy/zQyMv80MjL/NDIy/zQyMv80MjL/NDIy/zQy
>>leftover_icon.b64 echo Mv80MjL/NDIy/zQyMv80MjL/NDIy/zQyMv80MjL/NDIy/zQyMv80MjL/NDIy/zUzM/8uLCz/V1VV/7GwsP8oJib/OTc2/zUzM/81MzP/NTMz/zUzM/81MzP/
>>leftover_icon.b64 echo NTMz/zQyMv81MjL/NTMz/zUzM/80MjL/NDIy/zUzM/81MzP/NTMz/zUzM/81MzP/NTMz/zUzM/81MzP/NDIy/zQyMv81MzP/NTMy/zUzM/81MzP/OTc3/ygm
>>leftover_icon.b64 echo Jv+xsLD//v39/3FwcP8hHx//OTc3/zc1Nf81MzP/NTMz/zUzM/81MzP/NTMz/zUzM/82NDT/NjQ0/zUzM/81MzP/NTMz/zUzM/81MzP/NTMz/zUzM/81MzP/
>>leftover_icon.b64 echo NjQz/zUzM/81MzP/NTMz/zUzM/81MzP/NzU1/zk3N/8hHx//cW9v//3+/v/+/v7/9fX1/3Bvb/8qKCj/MC4u/zY0NP82NDT/NjQ0/zUzM/81MzP/NjQ0/zY0
>>leftover_icon.b64 echo NP82NDT/NjQ0/zY0NP82NDT/NTMz/zY0NP82NDT/NTMz/zY0M/81MzP/NjQ0/zUzM/81MzP/NTMz/zUzM/81MzP/MC0t/yknJ/9vbm7/9PT0//7+/v/+/v7/
>>leftover_icon.b64 echo /////////////62srP9ZWFj/OTc3/zY0NP82NDT/NjQ0/zY0NP82NDT/NjQ0/zY0NP82NDT/NTMz/zY0NP82NDT/NjQ0/zY0NP82NDT/NjQ0/zY0NP82MzP/
>>leftover_icon.b64 echo NjQ0/zY0M/81MzP/ODY2/1lXV/+trKz////////////+/v7/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
>>leftover_icon.b64 echo AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
"%PY%" -c "import base64,pathlib; pathlib.Path('leftover_icon_32.ico').write_bytes(base64.b64decode(pathlib.Path('leftover_icon.b64').read_text().replace(chr(10),'').replace(chr(13),'')))"
if not exist leftover_icon_32.ico (
  echo The icon file was not written.
  pause
  exit /b 1
)
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install pyinstaller
if errorlevel 1 (
  echo pip could not install PyInstaller.
  pause
  exit /b 1
)
set "VER="
if exist version_info.txt set "VER=--version-file version_info.txt"
del /q "Leftover's.spec" "Leftover's Setup.spec" 2>nul
echo.
echo Building Leftover's...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed --name "Leftover's" %VER% --icon leftover_icon_32.ico --add-data "leftover_icon_32.ico;." leftover_drive_scan.py
if errorlevel 1 (
  echo Cleaner build failed.
  pause
  exit /b 1
)
echo.
echo Building the setup wizard...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed --name "Leftover's Setup" %VER% --icon leftover_icon_32.ico --add-data "leftover_icon_32.ico;." --add-data "dist\Leftover's.exe;." setup_wizard.py
if errorlevel 1 (
  echo Setup build failed.
  pause
  exit /b 1
)
echo.
echo Done.
echo   %cd%\dist\Leftover's.exe
echo   %cd%\dist\Leftover's Setup.exe
pause
endlocal
