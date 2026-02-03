import argparse
import time
from PIL import Image, ImageDraw
from pycoral.adapters import common
from pycoral.adapters import detect
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter

# --- REFINERY CONFIGURATION ---
# Normalized coordinates (0 to 1000) for a sample restricted area
DANGER_ZONE = {'xmin': 300, 'ymin': 200, 'xmax': 700, 'ymax': 600}

def is_inside_danger_zone(obj_bbox, zone):
    """Calculates overlap between the worker and the restricted area."""
    return not (obj_bbox.xmin > zone['xmax'] or 
                obj_bbox.xmax < zone['xmin'] or 
                obj_bbox.ymin > zone['ymax'] or 
                obj_bbox.ymax < zone['ymin'])

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-m', '--model', required=True, help='File path of .tflite file')
    parser.add_argument('-i', '--input', required=True, help='File path of image to process')
    parser.add_argument('-l', '--labels', required=True, help='File path of labels file')
    parser.add_argument('-o', '--output', help='File path for the result image')
    args = parser.parse_args()

    labels = read_label_file(args.labels)
    interpreter = make_interpreter(args.model)
    interpreter.allocate_tensors()

    image = Image.open(args.input)
    _, scale = common.set_resized_input(
        interpreter, image.size, lambda size: image.resize(size, Image.LANCZOS))

    print('Processing Refinery Feed...')
    interpreter.invoke()
    objs = detect.get_objects(interpreter, 0.4, scale)

    if args.output:
        image = image.convert('RGB')
        draw = ImageDraw.Draw(image)
        # Draw the restricted zone
        draw.rectangle([(DANGER_ZONE['xmin'], DANGER_ZONE['ymin']), 
                        (DANGER_ZONE['xmax'], DANGER_ZONE['ymax'])], outline='yellow', width=5)
        
        for obj in objs:
            if labels.get(obj.id) == 'person':
                color = 'red' if is_inside_danger_zone(obj.bbox, DANGER_ZONE) else 'green'
                bbox = obj.bbox
                draw.rectangle([(bbox.xmin, bbox.ymin), (bbox.xmax, bbox.ymax)], outline=color, width=3)
                if color == 'red':
                    print(f"!!! ALERT: UNAUTHORIZED ENTRY DETECTED !!!")

        image.save(args.output)
        print(f'Report saved to {args.output}')

if __name__ == '__main__':
    main()