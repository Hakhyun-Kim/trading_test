import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test imports
try:
    from upbit_bot.kimchi_premium import KimchiPremiumCalculator, KimchiPremiumStrategy
    print("✅ Kimchi Premium imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test basic functionality
try:
    calc = KimchiPremiumCalculator()
    print("✅ KimchiPremiumCalculator created")
    
    strategy = KimchiPremiumStrategy()
    print("✅ KimchiPremiumStrategy created")
    
    print("✅ All kimchi premium components working!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc() 