import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lcd_manager import LcdManager

def test_lcd():
    print("--- TEST LCD MANAGER ---")
    print("Regardez l'écran...")
    
    # CS Pin 0 (CE0)
    lcd = LcdManager(cs_pin=0)
    
    lcd.clear()
    lcd.afficher_texte_fixe("TEST")
    time.sleep(2)
    
    lcd.scroll_text("BRAVO")
    time.sleep(1)
    
    lcd.clear()
    print("✅ Fin du test visuel")

if __name__ == "__main__":
    test_lcd()
