; ==========================================================================
; SEMS Pro — Inno Setup Installer Script
; Genera el instalador formal para distribución en Windows
; Compilar con: iscc installer.iss
; ==========================================================================

#define MyAppName "SEMS Pro"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "SEMS Pro"
#define MyAppExeName "Envio_Masivo_Seguro.exe"

[Setup]
; Identificador único de la aplicación (GUID generado para SEMS Pro)
AppId={{B3F7A2E1-9C4D-4E8A-B6F1-2D5E8A3C7F90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Pantalla de acuerdo de licencia
LicenseFile=EULA.txt
; Directorio de salida del instalador
OutputDir=dist\installer
OutputBaseFilename=SEMS_Pro_Setup_{#MyAppVersion}
; Icono del instalador y de la app
SetupIconFile=img\iconoSems.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Compresión máxima LZMA2
Compression=lzma2/ultra64
SolidCompression=yes
; Requiere privilegios de administrador para instalar en Program Files
PrivilegesRequired=admin
; Arquitectura
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; UI del instalador
WizardStyle=modern
WizardSizePercent=100
; Información adicional en "Agregar o quitar programas"
UninstallDisplayName={#MyAppName}
; Idioma
ShowLanguageDialog=no
; --------------------------------------------------------------------------
; FIRMA DE CÓDIGO (recomendado para eliminar la advertencia de SmartScreen):
; 1. Configurar en el IDE de Inno Setup: Tools > Configure Sign Tools...
;    Nombre: signtool | Comando: signtool.exe sign /fd SHA256 /tm http://timestamp.digicert.com /a $f
; 2. Descomentar las dos líneas siguientes para firmar instalador y desinstalador:
; SignTool=signtool
; SignedUninstaller=yes
; --------------------------------------------------------------------------

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el &Escritorio"; GroupDescription: "Accesos directos:"

[Files]
; Aplicación completa generada por PyInstaller en modo onedir (dist\Envio_Masivo_Seguro\)
Source: "dist\Envio_Masivo_Seguro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Icono de la aplicación
Source: "img\iconoSems.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Crear estructura de directorios de trabajo
Name: "{app}\data\input"; Permissions: users-modify
Name: "{app}\data\temp"; Permissions: users-modify

[Icons]
; Acceso directo en Menú Inicio
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\iconoSems.ico"; WorkingDir: "{app}"
; Acceso directo en Escritorio (opcional, marcado por defecto)
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\iconoSems.ico"; WorkingDir: "{app}"; Tasks: desktopicon
; Enlace para desinstalar en Menú Inicio
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Opción para ejecutar la app al finalizar la instalación
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName}"; Flags: nowait postinstall skipifsilent
