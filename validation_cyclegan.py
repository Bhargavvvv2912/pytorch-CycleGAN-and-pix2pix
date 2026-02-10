import sys
import os
import torch
import numpy as np
from PIL import Image

# Ensure the current directory is in python path
sys.path.append(os.getcwd())

def validate_cyclegan():
    print("--- 🎨 CycleGAN Deep Validation ---")
    
    try:
        # 1. THE INTERPOLATION TRAP (Pillow 10+ / NumPy 2.0 Conflict)
        # Legacy CycleGAN code uses Image.BILINEAR. 
        # Modern Pillow (2025/2026) has DELETED this in favor of Resampling.BILINEAR.
        try:
            interp_mode = Image.BILINEAR
            print(f"SUCCESS: Legacy Pillow constant found: {interp_mode}")
        except AttributeError:
            print("CRITICAL: API DEPLETION! 'Image.BILINEAR' has been removed in modern Pillow.")
            return False

        # 2. THE REPO LOGIC CHECK
        from models import networks
        print("SUCCESS: Internal 'models.networks' imported.")

        # 3. GENERATOR INSTANTIATION
        # We test if the environment can handle the model logic
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        netG = networks.define_G(
            input_nc=3, output_nc=3, ngf=64, 
            netG='resnet_9blocks', norm='instance', 
            use_dropout=False, init_type='normal', init_gain=0.02
        )
        netG.to(device)
        print(f"SUCCESS: Generator initialized on {device}.")

        # 4. FORWARD PASS
        dummy_input = torch.randn(1, 3, 256, 256).to(device)
        with torch.no_grad():
            output = netG(dummy_input)
        
        if output.shape == (1, 3, 256, 256):
            print(f"SUCCESS: Forward pass verified. Shape: {output.shape}")
            return True

    except Exception as e:
        print(f"\nCRITICAL: ENVIRONMENT DECAY DETECTED!")
        print(f"Failure: {type(e).__name__} - {e}")
        return False

if __name__ == "__main__":
    if validate_cyclegan():
        print("\n--- BASELINE GREEN ---")
        sys.exit(0)
    else:
        print("\n--- VALIDATION RED ---")
        sys.exit(1)