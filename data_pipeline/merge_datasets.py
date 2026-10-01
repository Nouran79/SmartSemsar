import pandas as pd
import numpy as np

def merge_pf_and_cubicasa(pf_csv_path, cubicasa_csv_path, output_merged_path="final_merged_dataset.csv"):
    print("📖 جاري تحميل بيانات Property Finder و CubiCasa...")
    df_pf = pd.read_csv(pf_csv_path)
    df_cc = pd.read_csv(cubicasa_csv_path)
    
    merged_rows = []
    print("🔗 جاري مطابقة كل عقار مع أنسب مخطط معماري وصورته...")
    
    for _, prop in df_pf.iterrows():
        p_beds = int(prop['bedrooms'])
        p_baths = int(prop['bathrooms'])
        p_area = float(prop['area_sqm'])
        
        # 1. التصفية حسب عدد الغرف والحمامات
        candidates = df_cc[
            (df_cc['svg_bedrooms'] == p_beds) & 
            (df_cc['svg_bathrooms'] == p_baths)
        ]
        
        if candidates.empty:
            candidates = df_cc[df_cc['svg_bedrooms'] == p_beds]
            
        if candidates.empty:
            candidates = df_cc
            
        # 2. المطابقة بأقرب مساحة
        size_diffs = np.abs(candidates['svg_area_sqm'] - p_area)
        best_match = candidates.loc[size_diffs.idxmin()]
        
        # دمج البيانات
        merged_rows.append({
            'property_id': prop['property_id'],
            'title': prop['title'],
            'price': prop['price'],
            'location': prop['location'],
            'pf_bedrooms': p_beds,
            'pf_bathrooms': p_baths,
            'pf_area_sqm': p_area,
            
            # بيانات المخطط والصورة من CubiCasa
            'cubicasa_id': best_match['cubicasa_id'],
            'matched_svg_path': best_match['svg_path'],
            'matched_image_path': best_match['image_path'],
            'svg_bedrooms': best_match['svg_bedrooms'],
            'svg_bathrooms': best_match['svg_bathrooms'],
            'svg_area_sqm': best_match['svg_area_sqm'],
            'area_diff_sqm': round(abs(best_match['svg_area_sqm'] - p_area), 2)
        })
        
    df_merged = pd.DataFrame(merged_rows)
    df_merged.to_csv(output_merged_path, index=False, encoding='utf-8-sig')
    print(f"🎉 تم دمج الداتاسيت بنجاح وحفظ الملف النهائي في: {output_merged_path}")

if __name__ == "__main__":
    merge_pf_and_cubicasa(
        pf_csv_path="./data/property_finder_data.csv",
        cubicasa_csv_path="cubicasa_parsed.csv",
        output_merged_path="final_merged_dataset.csv"
    )