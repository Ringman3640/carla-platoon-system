@echo off
set /p numWindows="Number of platoon vehicles to spawn: "
set /a n = 1
set /a count = %numWindows% + 1

:loop
start cmd /c PlatoonVehicle.py
set /a n = %n% + 1
IF %n% LSS %count% ( goto loop )
goto rest

:rest