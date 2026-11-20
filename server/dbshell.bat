@echo off
REM ReFind – connect to Neon PostgreSQL with psql
REM Usage: dbshell.bat                   (interactive shell)
REM        dbshell.bat -c "SELECT 1;"    (run a single command)

SET PGBINDIR=C:\Program Files\PostgreSQL\18\bin
SET PGURI=postgresql://neondb_owner:npg_ZgdM2bDJ6ynV@ep-nameless-night-az1j5ws1-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require^&channel_binding=require

"%PGBINDIR%\psql.exe" "%PGURI%" %*
