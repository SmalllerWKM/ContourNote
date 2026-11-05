#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <wchar.h>

/* Native windowed launcher: no shell, Python installation, PATH, or terminal. */
int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR args, int show) {
    wchar_t base[32768], python[32768], script[32768], command[32768];
    DWORD length = GetModuleFileNameW(NULL, base, 32768);
    if (!length || length >= 32768) return 1;
    wchar_t *slash = wcsrchr(base, L'\\');
    if (!slash) return 1;
    *slash = L'\0';
    if (wcslen(base)*2 + wcslen(args) + 160 >= 32768) return 1;
    wcscpy(python, base); wcscat(python, L"\\runtime\\pythonw.exe");
    wcscpy(script, base); wcscat(script, L"\\app\\run.py");
    if (GetFileAttributesW(python) == INVALID_FILE_ATTRIBUTES || GetFileAttributesW(script) == INVALID_FILE_ATTRIBUTES) {
        MessageBoxW(NULL, L"请先解压完整文件夹，再双击临绘.exe。请勿单独移动 EXE 文件。", L"临绘", MB_OK | MB_ICONERROR);
        return 1;
    }
    wcscpy(command, L"\""); wcscat(command, python); wcscat(command, L"\" -I \"");
    wcscat(command, script); wcscat(command, L"\" "); wcscat(command, args);
    SetEnvironmentVariableW(L"PYTHONHOME", NULL);
    SetEnvironmentVariableW(L"PYTHONPATH", NULL);
    STARTUPINFOW startup = {0}; startup.cb = sizeof(startup);
    PROCESS_INFORMATION process = {0};
    if (!CreateProcessW(python, command, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, base, &startup, &process)) {
        MessageBoxW(NULL, L"无法启动内置运行环境。请确认文件已完整解压。", L"临绘", MB_OK | MB_ICONERROR);
        return 1;
    }
    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD code = 1; GetExitCodeProcess(process.hProcess, &code); CloseHandle(process.hProcess);
    if (code) MessageBoxW(NULL, L"应用未能正常启动或运行。详细日志位于 %LOCALAPPDATA%\\ContourNote\\startup.log。", L"临绘", MB_OK | MB_ICONERROR);
    return (int)code;
}
