@echo off
REM ============================================================================
REM  SEMS Pro - Compilacion completa
REM  Ejecuta: tests -> limpieza -> PyInstaller -> Inno Setup
REM  Uso: doble clic, o desde CMD en la raiz del proyecto:  compilar.bat
REM ============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo   SEMS Pro - Compilacion completa
echo ============================================================
echo.

REM ---------------------------------------------------------------- 1. TESTS
echo [1/5] Ejecutando suite de pruebas...
python -m unittest discover -s tests
if errorlevel 1 (
    echo.
    echo   ERROR: Las pruebas no pasaron. Se detiene la compilacion.
    echo   Revise los fallos antes de generar el ejecutable.
    echo.
    pause
    exit /b 1
)
echo   OK - Todas las pruebas pasaron.
echo.

REM ------------------------------------------------------- 2. DEPENDENCIAS
echo [2/5] Verificando dependencias...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo   ERROR: Fallo la instalacion de dependencias.
    pause
    exit /b 1
)
echo   OK - Dependencias al dia.
echo.

REM --------------------------------------------------------- 3. LIMPIEZA
echo [3/5] Limpiando compilacion anterior...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
echo   OK - Directorios build y dist eliminados.
echo.

REM ------------------------------------------------------ 4. PYINSTALLER
echo [4/5] Compilando ejecutable con PyInstaller...
pyinstaller Envio_Masivo_Seguro.spec --noconfirm --log-level WARN
if errorlevel 1 (
    echo.
    echo   ERROR: Fallo la compilacion con PyInstaller.
    pause
    exit /b 1
)
if not exist "dist\Envio_Masivo_Seguro\Envio_Masivo_Seguro.exe" (
    echo.
    echo   ERROR: No se genero el ejecutable esperado.
    pause
    exit /b 1
)
echo   OK - Ejecutable generado.
echo.

REM -- Revision de advertencias relevantes en el reporte de PyInstaller
echo   Revisando advertencias criticas...
set "WARNFILE=build\Envio_Masivo_Seguro\warn-Envio_Masivo_Seguro.txt"
if exist "%WARNFILE%" (
    findstr /i /c:"keyring" /c:"win32ctypes" /c:"pikepdf" /c:"cryptography" "%WARNFILE%" >nul 2>&1
    if not errorlevel 1 (
        echo.
        echo   AVISO: Hay menciones a keyring/win32ctypes/pikepdf/cryptography
        echo          en el reporte de advertencias. Revise:
        echo          %WARNFILE%
        echo.
        echo          Nota: las entradas de win32ctypes.core._common y similares
        echo          son artefactos esperados de su carga dinamica y NO indican
        echo          un problema. La prueba real es ejecutar la aplicacion.
        echo.
    ) else (
        echo   OK - Sin advertencias criticas.
    )
)
echo.

REM ------------------------------------------------------- 5. INNO SETUP
echo [5/5] Generando instalador con Inno Setup...
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe"      set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
where iscc >nul 2>&1 && set "ISCC=iscc"

if "!ISCC!"=="" (
    echo.
    echo   AVISO: No se encontro Inno Setup ^(ISCC.exe^).
    echo   El ejecutable SI quedo listo en: dist\Envio_Masivo_Seguro\
    echo   Para generar el instalador, instale Inno Setup 6 desde:
    echo     https://jrsoftware.org/isdl.php
    echo   y vuelva a ejecutar este script.
    echo.
    goto :RESUMEN
)

"!ISCC!" installer.iss
if errorlevel 1 (
    echo.
    echo   ERROR: Fallo la generacion del instalador.
    pause
    exit /b 1
)
echo   OK - Instalador generado.
echo.

:RESUMEN
echo ============================================================
echo   COMPILACION FINALIZADA
echo ============================================================
echo.
echo   Ejecutable:  dist\Envio_Masivo_Seguro\Envio_Masivo_Seguro.exe
if exist "dist\installer" (
    echo   Instalador:  dist\installer\
    dir /b "dist\installer\*.exe" 2>nul
)
echo.
echo   ANTES DE LLEVARLO AL CLIENTE, VERIFIQUE:
echo     1. La aplicacion abre sin ventana de error
echo     2. Lee la licencia del Administrador de Credenciales
echo     3. Guarda las credenciales SMTP en Configuracion
echo     4. Al cerrar y reabrir, entra directo
echo     5. El prefijo y sufijo de contrasena estan configurados
echo.
pause
