@echo off
REM Redespliega FutbolApp en el servidor Contabo (147.93.181.76).
REM Trae lo ultimo de la rama main de GitHub y reconstruye el contenedor.
REM La pagina queda en https://147-93-181-76.sslip.io
echo Redesplegando FutbolApp en Contabo...
ssh -i "%USERPROFILE%\.ssh\futbolapp_vps" -p 22 -o StrictHostKeyChecking=no root@147.93.181.76 "bash /opt/futbolapp/redeploy.sh"
echo.
pause
