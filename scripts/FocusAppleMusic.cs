// Compile with:
//   C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /r:UIAutomationClient.dll /r:UIAutomationTypes.dll FocusAppleMusic.cs
// Demonstrates attaching to the interactive "Default" desktop before enumerating WinUI 3 / UWP windows.

using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Automation;

public class FocusAppleMusic {
    [DllImport("user32.dll")] static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);
    [DllImport("user32.dll")] static extern bool SetThreadDesktop(IntPtr hDesktop);
    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr hWnd);

    public static void Main() {
        SetProcessDPIAware();
        IntPtr hd = OpenDesktop("Default", 0, false, 0x01FF);
        if (hd != IntPtr.Zero) SetThreadDesktop(hd);

        var wins = AutomationElement.RootElement.FindAll(TreeScope.Children, Condition.TrueCondition);
        foreach (AutomationElement w in wins) {
            int pid = w.Current.ProcessId;
            string pname = "";
            try { pname = Process.GetProcessById(pid).ProcessName; } catch { }
            if (pname.Equals("AppleMusic", StringComparison.OrdinalIgnoreCase) &&
                w.Current.Name == "Apple Music") {
                IntPtr hwnd = (IntPtr)w.Current.NativeWindowHandle;
                Console.WriteLine("Found Apple Music HWND: 0x" + hwnd.ToString("X"));
                ShowWindow(hwnd, 3); // SW_MAXIMIZE
                SetForegroundWindow(hwnd);
                return;
            }
        }
        Console.WriteLine("Apple Music window not found.");
    }
}
