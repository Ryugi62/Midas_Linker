import win32gui
import win32api
import win32con
import ctypes
from ctypes import wintypes

def get_target_window_info(target_hwnd):
    rect = win32gui.GetWindowRect(target_hwnd)
    x = rect[0]
    y = rect[1]
    width = rect[2] - rect[0]
    height = rect[3] - rect[1]
    return x, y, width, height

def get_window_z_order(hwnd):
    """특정 윈도우의 Z-Order를 반환하는 함수"""
    z = 0
    current_hwnd = win32gui.GetTopWindow(None)
    while current_hwnd:
        if current_hwnd == hwnd:
            return z
        current_hwnd = win32gui.GetWindow(current_hwnd, win32con.GW_HWNDNEXT)
        z += 1
    return -1  # 윈도우를 찾지 못한 경우

class OverlayWindow:
    def __init__(self, target_hwnd):
        self.target_hwnd = target_hwnd
        self.prev_x = self.prev_y = self.prev_width = self.prev_height = None

        hInstance = win32api.GetModuleHandle()
        className = 'MyOverlayWindowClass'
        
        # Define window class
        wndClass                = win32gui.WNDCLASS()
        wndClass.style          = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        wndClass.lpfnWndProc    = self.WndProc
        wndClass.hInstance      = hInstance
        wndClass.hCursor        = win32gui.LoadCursor(None, win32con.IDC_ARROW)
        wndClass.hbrBackground  = win32gui.CreateSolidBrush(win32api.RGB(0, 0, 0))
        wndClass.lpszClassName  = className

        self.classAtom = win32gui.RegisterClass(wndClass)
        
        exStyle = win32con.WS_EX_LAYERED
        style = win32con.WS_POPUP

        # Create the window
        self.hwnd = win32gui.CreateWindowEx(
            exStyle,
            self.classAtom,
            None,  # No window title
            style,
            0, 0, 0, 0,
            None, None, hInstance, None)

        # Set window to black background and 50% transparency
        win32gui.SetLayeredWindowAttributes(self.hwnd, 0, int(255 * 0.5), win32con.LWA_ALPHA)
        # Show the window
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)

        # Set a timer using ctypes
        self.timer_id = ctypes.windll.user32.SetTimer(self.hwnd, 1, 10, None)
        if not self.timer_id:
            print("Failed to create timer.")
            win32gui.DestroyWindow(self.hwnd)

    def WndProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_DESTROY:
            ctypes.windll.user32.KillTimer(self.hwnd, self.timer_id)
            win32gui.PostQuitMessage(0)
            return 0
        elif msg == win32con.WM_TIMER:
            self.on_timer()
            return 0
        elif msg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(hwnd)
            # No painting required
            win32gui.EndPaint(hwnd, ps)
            return 0
        elif msg in (win32con.WM_LBUTTONDOWN, win32con.WM_RBUTTONDOWN, win32con.WM_MBUTTONDOWN,
                     win32con.WM_LBUTTONUP, win32con.WM_RBUTTONUP, win32con.WM_MBUTTONUP,
                     win32con.WM_MOUSEMOVE, win32con.WM_MOUSEWHEEL):
            # Block mouse events from passing through
            return 0
        elif msg == win32con.WM_SETCURSOR:
            # 마우스 커서 설정
            win32gui.SetCursor(win32gui.LoadCursor(None, win32con.IDC_ARROW))
            return True
        else:
            return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)
        
    def on_timer(self):
        if not win32gui.IsWindow(self.target_hwnd):
            # Target window no longer exists
            win32gui.DestroyWindow(self.hwnd)
            return

        x, y, width, height = get_target_window_info(self.target_hwnd)
        x -= 10
        y -= 10
        width += 20
        height += 20

        if (x != self.prev_x or y != self.prev_y or width != self.prev_width or height != self.prev_height):
            # Update overlay window position and size
            flags = win32con.SWP_NOACTIVATE
            # Get the window above the target window
            prev_hwnd = win32gui.GetWindow(self.target_hwnd, win32con.GW_HWNDPREV)
            if prev_hwnd == 0:
                # If target window is at the top, set overlay to topmost
                hWndInsertAfter = win32con.HWND_TOPMOST
            else:
                hWndInsertAfter = prev_hwnd
            win32gui.SetWindowPos(self.hwnd, hWndInsertAfter, x, y, width, height, flags)
            self.prev_x, self.prev_y, self.prev_width, self.prev_height = x, y, width, height
        else:
            # Ensure overlay window is above target_hwnd
            flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
            prev_hwnd = win32gui.GetWindow(self.target_hwnd, win32con.GW_HWNDPREV)
            if prev_hwnd == 0:
                hWndInsertAfter = win32con.HWND_TOPMOST
            else:
                hWndInsertAfter = prev_hwnd
            win32gui.SetWindowPos(self.hwnd, hWndInsertAfter, 0, 0, 0, 0, flags)

        # Z-Order 출력
        overlay_z_order = get_window_z_order(self.hwnd)
        target_z_order = get_window_z_order(self.target_hwnd)
        print(f"Overlay Z-order: {overlay_z_order}, Target Z-order: {target_z_order}")

    def run(self):
        win32gui.PumpMessages()

def main(target_hwnd):
    overlay = OverlayWindow(target_hwnd)
    overlay.run()

if __name__ == '__main__':
    # 대상 윈도우 제목을 사용하여 핸들 얻기
    target_title = '파일 탐색기'  # 여기에 대상 윈도우의 제목을 입력하세요
    target_hwnd = win32gui.FindWindow(None, target_title)
    if target_hwnd:
        main(target_hwnd)
    else:
        print('Target window not found.')
