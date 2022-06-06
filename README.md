# servoscreen

Remote display utility for Servo-i (HBO) Ventilators.

Servoscreen is based on the Servo-i Computer Interface Emulator (CIE). It communicates with the ventilator via RS232 and displays various metrics. The programs intended use is in hyperbaric medicine, where real-time data display is not available external to the ventilator unit inside of a pressure chamber.

pyinstaller __main__.py --clean -F -d all -w
