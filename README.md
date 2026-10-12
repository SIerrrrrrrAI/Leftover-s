Leftover's  finds folders left behind after programs are removed, plus caches and temporary files that no longer belong to an installed application. It is a Windows cleanup tool. It is not a full disk wipe, and it does not uninstall Windows.

The goal is to show you space that looks safe to reclaim, then let you choose what goes to the Recycle Bin. Nothing is deleted until you select it and confirm. Dry-run is on the first time you open the program, so a delete only writes a practice line in the log until you turn Dry-run off.

What it looks for

The scan checks the drives you select. That includes Program Files, Program Files (x86), ProgramData, AppData, and Windows Temp. A folder is listed only when it looks like leftover data: no matching installed program, no running process or service, and no real program file inside it.

If the scan finds a normal program .exe or shortcut in a folder, it stops on that folder and moves on. Those folders are not offered for deletion. When the scan finishes, a dialog and the agent window list the folders that were stopped for that reason.

What it will not list

These are skipped even if they are large:





Windows itself, including System32, drivers, boot, and recovery



Microsoft components such as Edge, Defender, the Store, and .NET



Hardware and PC-maker folders such as NVIDIA, Intel, AMD, Realtek, Dell, HP, Lenovo, ASUS, MSI, and Acer



Nahimic and A-Volute



A folder that still belongs to an installed program



A folder a running program or Windows service is using



Documents, pictures, music, video, and the desktop

The local assistant cannot override those rules. It may suggest extra folders. The program checks every suggestion again and refuses anything protected.

How to use it





Open Leftover Drive Scan.



Leave Dry-run on until you trust the list.



Choose the drives to scan and click Scan.



Read the path, size, confidence, and the reason on each row.



Click the box, or right-click a row, to select it. Right-click can also open the folder, copy the path, or start a leftover uninstaller.



Click Delete selected. With Dry-run on, nothing is removed. With Dry-run off, the folder is sent to the Recycle Bin.



Use the Recently deleted tab to see what this tool and the Recycle Bin already removed.

Deleting from Program Files usually needs the Relaunch as admin button.

The local assistant

The assistant is optional. It runs on your PC through Ollama. It does not send the scan to the internet, and it cannot delete files. When the program opens, an agent window shows a short greeting, free space on your drives, the last scan time, and how much space earlier deletes restored.

Use Link AI if you want to choose or test the local model. The usual model is hermes3. That download is several gigabytes.

The setup program

LeftoverDriveScanSetup.exe installs the cleaner and asks before it adds anything else.





Python is optional. The cleaner program already includes it.



Ollama is needed only for the local assistant.



hermes3 is the optional local model.

You can ignore the Python source files if you only want to run the installed program

