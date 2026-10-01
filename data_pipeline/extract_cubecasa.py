import os
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np

def polygon_area(points_str):
    """حساب مساحة البوليجون من إحداثيات SVG (Shoelace Formula)"""
    try:
        coords = []
        for pair in points_str.strip().split():
            if ',' in pair:
                x, y = map(float, pair.split(','))
                coords.append((x, y))
        if len(coords) < 3:
            return 0.0
        x = [c[0] for c in coords]
        y = [c[1] for c in coords]
        return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
    except Exception:
        return 0.0

def parse_cubicasa_folder(folder_path):
    """قراءة ملف model.svg واختيار صورة F1_scaled.png"""
    svg_path = os.path.join(folder_path, 'model.svg')
    if not os.path.exists(svg_path):
        return None
        
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        bedrooms = 0
        bathrooms = 0
        indoor_pixel_area = 0.0
        
        for elem in root.iter():
            class_attr = elem.attrib.get('class', '')
            if 'Space' in class_attr:
                poly_elem = elem.find('{http://www.w3.org/2000/svg}polygon')
                if poly_elem is None:
                    poly_elem = elem.find('polygon')
                
                area = polygon_area(poly_elem.attrib.get('points', '')) if poly_elem is not None else 0.0
                
                # تصنيف الغرف حسب اختصارات CubiCasa5k الفنلندية/القياسية
                if any(k in class_attr for k in ['Bedroom', 'MH']):
                    bedrooms += 1
                    indoor_pixel_area += area
                elif any(k in class_attr for k in ['Bath', 'Shower', 'PH', 'WC']):
                    bathrooms += 1
                    indoor_pixel_area += area
                elif 'Space' in class_attr and not 'Outdoor' in class_attr:
                    indoor_pixel_area += area

        estimated_sqm = round(indoor_pixel_area * 0.0095, 2)
        
        # اختيار صورة واحدة فقط (F1_scaled.png كأولوية)
        selected_img_name = None
        for img in ['F1_scaled.png', 'F1_original.png', 'F2_scaled.png']:
            if os.path.exists(os.path.join(folder_path, img)):
                selected_img_name = img
                break
                
        if not selected_img_name:
            pngs = [f for f in os.listdir(folder_path) if f.endswith('.png')]
            selected_img_name = pngs[0] if pngs else None

        img_rel_path = os.path.join(folder_path, selected_img_name) if selected_img_name else None
        cubicasa_id = os.path.basename(folder_path)
        
        return {
            'cubicasa_id': cubicasa_id,
            'svg_path': svg_path,
            'image_file_name': selected_img_name,
            'image_path': img_rel_path,
            'svg_bedrooms': bedrooms,
            'svg_bathrooms': bathrooms,
            'svg_area_sqm': estimated_sqm
        }
    except Exception:
        return None

def build_cubicasa_csv(base_dir, output_csv="cubicasa_parsed.csv"):
    records = []
    print("🔍 جاري فحص ملفات SVG وصور CubiCasa5k...")
    
    for root_dir, dirs, files in os.walk(base_dir):
        if 'model.svg' in files:
            data = parse_cubicasa_folder(root_dir)
            if data:
                records.append(data)
                
    df = pd.DataFrame(records)
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"✅ تم معالجة {len(df)} مخطط بنجاح وحفظ البيانات في: {output_csv}")

if __name__ == "__main__":
    cubicasa_dir = "./data_pipeline/cubecasa"
    build_cubicasa_csv(cubicasa_dir, "cubicasa_parsed.csv")