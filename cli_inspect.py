import argparse
import os
import json
from defect_detector import WireMeshDefectDetector

def main():
    parser = argparse.ArgumentParser(description="AI Manufacturing Defect Detection CLI Tool")
    parser.add_argument("--image", type=str, required=True, help="Path to input product image")
    parser.add_argument("--save-output", action="store_true", help="Save annotated inspection images to output folder")
    parser.add_argument("--output-dir", type=str, default="inspection_results", help="Directory to save inspection outputs")
    
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"Error: File '{args.image}' does not exist.")
        return

    print("=" * 60)
    print(" AI MANUFACTURING DEFECT INSPECTION ENGINE ")
    print(" Target Product: Finished Wire Mesh / Welded Grid ")
    print("=" * 60)

    detector = WireMeshDefectDetector()
    result = detector.inspect_image(args.image)

    print(f"\n[FILE]: {result['filename']}")
    print(f"[VERDICT]: {result['verdict']}")
    print(f"[QUALITY SCORE]: {result['quality_score']}%")
    print(f"[METRICS]:")
    for k, v in result['metrics'].items():
        print(f"  - {k}: {v}")

    print(f"\n[DETECTED DEFECTS] ({len(result['defects'])} total):")
    if len(result['defects']) == 0:
        print("  ✓ No defects detected. Product meets quality assurance standards.")
    else:
        for idx, d in enumerate(result['defects'], 1):
            print(f"  {idx}. [{d['severity']}] {d['type']}")
            print(f"     Description: {d['description']}")
            print(f"     Confidence: {d['confidence'] * 100:.1f}%")

    if args.save_output:
        os.makedirs(args.output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(args.image))[0]
        
        # Save JSON result
        json_path = os.path.join(args.output_dir, f"{base_name}_result.json")
        clean_result = {k: v for k, v in result.items() if k != 'images'}
        with open(json_path, 'w') as f:
            json.dump(clean_result, f, indent=2)
        
        print(f"\n[SAVED]: Inspection report saved to {json_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
