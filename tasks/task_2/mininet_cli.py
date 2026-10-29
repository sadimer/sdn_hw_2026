"""Same topology as Task 1; use the Task 2 controller on TCP/6653."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.task_1.mininet_cli import main
from mininet.log import setLogLevel

if __name__ == '__main__':
    setLogLevel('info')
    main()
