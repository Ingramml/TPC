"""
VS Code Integration Helper for TPC Pipeline
Provides better integration with VS Code for notifications and status updates
"""

import os
import json
import subprocess
import platform
from datetime import datetime


def send_vscode_notification(title, message, type="info"):
    """
    Send notification that works well with VS Code
    
    Args:
        title (str): Notification title
        message (str): Notification message  
        type (str): Type of notification ('info', 'warning', 'error')
    """
    try:
        # Write status to a file that VS Code can monitor
        status_file = os.path.join(os.getcwd(), '.tpc_status.json')
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "message": message,
            "type": type,
            "status": "complete" if type == "info" else "error"
        }
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
        
        # Also send system notification
        send_system_notification(title, message)
        
        # Print to console for VS Code terminal
        emoji = "✅" if type == "info" else "❌" if type == "error" else "⚠️"
        print(f"\n{emoji} {title}: {message}")
        print("=" * 50)
        
    except Exception as e:
        print(f"Failed to send VS Code notification: {e}")


def send_system_notification(title, message):
    """Send OS-level notification"""
    try:
        system = platform.system()
        
        if system == "Darwin":  # macOS
            script = f'''
            display notification "{message}" with title "{title}" sound name "Glass"
            '''
            subprocess.run(['osascript', '-e', script], timeout=5)
            
        elif system == "Windows":  # Windows
            # Use Windows toast notification
            subprocess.run([
                'powershell', '-Command',
                f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms"); [System.Windows.Forms.MessageBox]::Show("{message}", "{title}")'
            ], timeout=5)
            
        elif system == "Linux":  # Linux
            subprocess.run(['notify-send', title, message], timeout=5)
            
    except Exception:
        pass  # Fail silently if notifications don't work


def play_completion_sound():
    """Play completion sound optimized for VS Code usage"""
    try:
        system = platform.system()
        
        if system == "Darwin":  # macOS
            # Use system sound that works well in development
            os.system('afplay /System/Library/Sounds/Glass.aiff &')
        elif system == "Windows":  # Windows
            import winsound
            winsound.Beep(1000, 500)
        else:
            # Fallback - terminal bell
            print('\a')
            
    except Exception:
        print('\a')  # Fallback bell


def create_vscode_output_channel(channel_name="TPC Pipeline"):
    """
    Create output that appears in VS Code's output panel
    """
    print(f"\n=== {channel_name} Output ===")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)


def finish_vscode_output():
    """
    Finish VS Code output with clear completion indicator
    """
    print("\n" + "=" * 50)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎉 PIPELINE COMPLETE 🎉")
    print("=" * 50)
    
    # Play sound and send notification
    play_completion_sound()
    send_vscode_notification(
        "TPC Pipeline Complete", 
        "Processing finished successfully", 
        "info"
    )


# Example integration with existing code
if __name__ == '__main__':
    # Test the VS Code integration
    create_vscode_output_channel("TPC Test")
    
    import time
    print("Testing VS Code integration...")
    time.sleep(1)
    
    finish_vscode_output()
