pyinstaller --onefile --add-data "afbeeldingen;afbeeldingen" --add-data "fonts;fonts" --add-data "geluiden;geluiden" start.py
pyinstaller --onefile --add-data "afbeeldingen;afbeeldingen" --add-data "fonts;fonts" --add-data "geluiden;geluiden" --hidden-import=examplelib start.py
