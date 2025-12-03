# validation_cyclegan.py

import sys
import os
import torch
import numpy as np

# Ensure the current directory is in python path so we can import 'models'
sys.path.append(os.getcwd())

def run_cyclegan_smoke_test():
    print("--- Starting CycleGAN Smoke Test ---")
    
    try:
        # --- Stage 1: Import Check ---
        # This checks if 'torch', 'dominate', 'visdom' etc are installed
        print("--> Stage 1: Importing core modules...")
        try:
            from models import networks
            print("    Successfully imported models.networks")
        except ImportError as e:
            # Common failure: missing 'dominate' or 'visdom'
            print(f"CRITICAL: Failed to import repo modules. Dependency missing? Error: {e}")
            raise e

        # --- Stage 2: Hardware/Backend Check ---
        print("\n--> Stage 2: Checking PyTorch backend...")
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"    Using device: {device}")
        
        # --- Stage 3: Model Instantiation ---
        # We attempt to build the ResnetGenerator.
        # This verifies that the PyTorch version syntax matches the repo code.
        print("\n--> Stage 3: Instantiating ResnetGenerator...")
        
        # These parameters match the default CycleGAN configuration
        netG = networks.define_G(
            input_nc=3, 
            output_nc=3, 
            ngf=64, 
            netG='resnet_9blocks', 
            norm='instance', 
            use_dropout=False, 
            init_type='normal', 
            init_gain=0.02, 
            gpu_ids=[] # Force CPU for the smoke test to ensure CI compatibility
        )
        print("    Generator instantiated successfully.")

        # --- Stage 4: Forward Pass (The Real Test) ---
        print("\n--> Stage 4: Running Forward Pass (Inference)...")
        
        # Create a random noise image tensor [Batch, Channels, Height, Width]
        # CycleGAN standard size is 256x256
        dummy_input = torch.randn(1, 3, 256, 256)
        
        # Run inference (no gradients needed for smoke test)
        with torch.no_grad():
            output = netG(dummy_input)
        
        # Verify Output Shape
        expected_shape = (1, 3, 256, 256)
        if output.shape != expected_shape:
            raise ValueError(f"Output shape mismatch! Expected {expected_shape}, got {output.shape}")
            
        print(f"    Forward pass successful. Output shape: {output.shape}")
        
        print("\n--- CycleGAN Smoke Test: ALL STAGES PASSED ---")
        sys.exit(0)

    except Exception as e:
        print(f"\n--- CycleGAN Smoke Test: FAILED ---", file=sys.stderr)
        print(f"Error: {type(e).__name__} - {e}", file=sys.stderr)
        # Uncomment for deeper debugging if needed
        # import traceback
        # traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_cyclegan_smoke_test()