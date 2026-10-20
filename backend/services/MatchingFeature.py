import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
import os
from backend.schema.state import CustomerRequirements
import os
import pandas as pd
from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field


# العميل بيكتب المكان بالعربي والداتا بالإنجليزي، والـ embeddings مش بتربطهم كويس ("الشيخ زايد" كانت بتجيب الزمالك):
# كلمة عربية -> أسماء المكان زي ما هي مكتوبة في عمود location
LOCATION_ALIASES = {
    "التجمع الخامس": ["The 5th Settlement"], "التجمع الاول": ["The 1st Settlement"], "التجمع": ["Settlement", "New Cairo"],
    "القاهرة الجديدة": ["New Cairo"], "نيو كايرو": ["New Cairo"], "القطامية": ["Katameya"], "الرحاب": ["Rehab"],
    "مدينتي": ["Madinaty"], "اللوتس": ["Lotus"], "النرجس": ["Narges"], "الاندلس": ["Andalus"], "هايد بارك": ["Hyde Park"],
    "زايد": ["Sheikh Zayed"], "اكتوبر": ["6 October"], "المعادي": ["Maadi"], "دجلة": ["Degla"], "الزمالك": ["Zamalek"],
    "جاردن سيتي": ["Garden City"], "مدينة نصر": ["Nasr City"], "الهرم": ["Haram"], "المقطم": ["Mokattam"],
    "اسكندرية": ["Alexandria"], "الاسكندرية": ["Alexandria"], "سموحة": ["Smouha"], "الشيخ زايد": ["Sheikh Zayed"],
}


# المساحة اللي العميل قالها ± 10% (180 متر -> من 162 لـ 198)
AREA_TOLERANCE = 0.10

# نوع العقار من العنوان (الداتا مفيهاش عمود للنوع)
PROPERTY_TYPE_WORDS = {
    "studio": ["studio"],
    "villa": ["villa", "stand alone", "standalone"],
    "duplex": ["duplex"],
    "townhouse": ["townhouse", "town house"],
}


def location_keywords(location_query: str) -> list:
    """الأسماء الإنجليزية للمكان اللي العميل كتبه (أطول تطابق الأول: "التجمع الخامس" قبل "التجمع")"""
    q = str(location_query).replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    for arabic in sorted(LOCATION_ALIASES, key=len, reverse=True):
        if arabic in q:
            return LOCATION_ALIASES[arabic]
    return []


class PropertyMatchingService:
    def __init__(self, csv_path: str, chroma_path: str):
        print("---enter---")
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        print("---after csv---")
        
        # 1. إعداد ChromaDB والـ Multilingual Embedding Function
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.client = chromadb.PersistentClient(path=chroma_path)
        
        self.collection = self.client.get_or_create_collection(
            name="properties_semantic", 
            embedding_function=self.ef
        )
        # الـ index مش بيترفع على git: لو فاضي (أول تشغيل على جهاز جديد)، نبنيه من الـ CSV،
        # وإلا ترتيب المكان بيرجع فاضي وكل بحث بيطلع 0 نتيجة
        if self.collection.count() == 0:
            self._build_location_index()
        print("---final---")

    def _build_location_index(self):
        """نفس اللي بيعمله data/scripts/index_embeddings.py: الموقع كنص + property_id كـ metadata للفلترة"""
        print(f"📦 Building location index for {len(self.df)} properties...")
        ids, documents, metadatas = [], [], []
        for idx, row in self.df.iterrows():
            prop_id = str(row.get('property_id', idx))
            location = str(row['location']) if pd.notna(row.get('location')) else ''
            ids.append(prop_id)
            documents.append(location.strip(" |") or "عقار بدون عنوان تفصيلي")
            metadatas.append({"property_id": prop_id, "location": location})
        for i in range(0, len(ids), 250):
            self.collection.add(ids=ids[i:i + 250], documents=documents[i:i + 250],
                                metadatas=metadatas[i:i + 250])

    def _filter_dataframe(self, reqs: CustomerRequirements) -> pd.DataFrame:
        """كل اللي العميل قاله شرط لازم يتحقق (مفيش تنازل عن أي شرط لو النتايج قليلة):
        الميزانية (أقصى وأدنى)، عدد الغرف بالظبط، المساحة في حدود AREA_TOLERANCE، ونوع العقار"""
        df = self.df
        if reqs.budget_max:
            df = df[df['price'] <= reqs.budget_max]
        if reqs.budget_min:
            df = df[df['price'] >= reqs.budget_min]
        if reqs.bedrooms:
            df = df[df['pf_bedrooms'] == reqs.bedrooms]
        if reqs.area_sqm:
            df = df[(df['pf_area_sqm'] - reqs.area_sqm).abs() <= reqs.area_sqm * AREA_TOLERANCE]
        type_words = PROPERTY_TYPE_WORDS.get(reqs.property_type)
        if type_words:          # شقة عادية مش بنفلترها: أغلب العناوين مش بتقول "apartment"
            df = df[df['title'].fillna('').str.contains('|'.join(type_words), case=False, regex=True)]
        return df

    def search_properties(self, reqs: CustomerRequirements = None, Purpose: str = "", top_k: int = 5) -> dict:
        """الشقق اللي بتحقق كل طلبات العميل، الأقرب للمساحة المطلوبة الأول. لو مفيش، بترجع فاضية"""
        if Purpose == "general_browse":
            return {
                "total_found": len(self.df),
                "used_fallback": False,
                "properties": self.df.copy().to_dict(orient='records')
            }

        print(f"\n📥 [Input Req] Location: '{reqs.location}' | Budget: {reqs.budget_min}-{reqs.budget_max} | "
              f"Rooms: {reqs.bedrooms} | Area: {reqs.area_sqm} | Type: {reqs.property_type}")
        candidates = self._filter_dataframe(reqs)
        results = self._rank_by_location(reqs.location, candidates, reqs.area_sqm, top_k)
        print(f"✅ {len(results)} matching properties")
        return {"total_found": len(results), "used_fallback": False, "properties": results}

    def _rank_by_location(self, location_query: str, candidates: pd.DataFrame, target_area: float = None,
                          top_k: int = 5) -> list:
        """المكان: لو اسمه معروف (زايد، التجمع، المعادي...) الشقق لازم تكون فيه؛ لو مش معروف،
        الـ embeddings بتجيب الأقرب. وبعدها الأقرب للمساحة المطلوبة (أو الأرخص) الأول"""
        if candidates.empty:
            return []

        if location_query:
            keywords = location_keywords(location_query)
            if keywords:
                in_area = candidates['location'].fillna('').str.contains('|'.join(keywords), case=False, regex=True)
                candidates = candidates[in_area]
            elif self.collection.count():
                ids = candidates['property_id'].astype(str).tolist()
                chroma_results = self.collection.query(
                    query_texts=[location_query], where={"property_id": {"$in": ids}},
                    n_results=min(top_k, len(ids)))
                matched_ids = chroma_results['ids'][0] if chroma_results['ids'] else []
                candidates = candidates[candidates['property_id'].astype(str).isin(matched_ids)]

        if target_area:
            candidates = candidates.assign(_diff=(candidates['pf_area_sqm'] - target_area).abs())
            candidates = candidates.sort_values(['_diff', 'price']).drop(columns='_diff')
        else:
            candidates = candidates.sort_values('price')
        return candidates.head(top_k).to_dict(orient='records')
    
    def get_property_by_id(self, property_id: str) -> dict:
        matched = self.df[self.df['property_id'].astype(str) == str(property_id)]
        if not matched.empty:
            return matched.iloc[0].to_dict()
        return None


# if __name__ == "__main__":
#     BASE_DIR = os.path.dirname(__file__)
#     CSV_PATH = os.path.abspath(os.path.join(BASE_DIR, "../data/final_merged_dataset.csv"))
#     CHROMA_PATH = os.path.abspath(os.path.join(BASE_DIR, "../data/chroma_db"))

#     matcher = PropertyMatchingService(csv_path=CSV_PATH, chroma_path=CHROMA_PATH)

#     # برومبت يطلب شقة في التجمع الخامس بسعر محدد
#     sample_requirements = {
#         "location_query": "شقة للبيع في التجمع الخامس", # عربي عادي
#         "max_price": 5000000,                            # 5 مليون
#         "bedrooms": 3,
#         "area_sqm": 150
#     }

#     final_properties = matcher.search_properties(sample_requirements)
#     print(f"\n✅ إجمالي العقارات المسترجعة: {len(final_properties)}")
#     for p in final_properties:
#         print(f"📌 [{p.get('property_id')}] -{p.get('title')} | السعر: {p.get('price')} | الموقع: {p.get('location')}")



# if __name__ == "__main__":
#     print("---lll---")
#     CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
#     print("---lll---")
#     # 2. الرجوع خطوتين للوصول لـ Root المشروع (PropTech-AI-Platform)
#     PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
#     print("---lll---")

#     # 3. تحديد مسارات الـ data و chroma الصح
#     CSV_PATH = os.path.join(PROJECT_ROOT, "data", "final_merged_dataset.csv")
#     print("---lll---")
#     CHROMA_PATH = os.path.join(PROJECT_ROOT, "data", "chroma_db")
#     print("---lll---")
#     # 1. تقومين بتهيئة الـ Service
#     matcher = PropertyMatchingService(csv_path=CSV_PATH, chroma_path=CHROMA_PATH)
#     print("---lll---")

#     # 2. تجهيز حالات تجريبية كـ CustomerRequirements Objects مباشرة
#     test_case_1 = CustomerRequirements(
#         location="التجمع الخامس",
#         budget_max=6000000.0,
#         bedrooms=3,
#         area_sqm=160.0,
#         property_type="apartment"
#     )
#     print("---lll---")

#     test_case_impossible_rooms = CustomerRequirements(
#         location="الشيخ زايد",
#         budget_max=3000000.0,
#         bedrooms=10, # شرط تعجيزي لتجربة الـ Fallback
#         area_sqm=500.0
#     )
#     print("---lll---")

#     # 3. تشغيل الفانكشن مباشرة بدون أي Nodes!
#     print("----------------------------------------")
#     print("🧪 Test 1: Normal Search")
#     res1 = matcher.search_properties(test_case_1)
#     print(f"✅ Total Found: {res1['total_found']} | Fallback Used: {res1['used_fallback']}")
#     print("🏠 [نتائج Test 1]:")
#     for idx, p in enumerate(res1['properties'], 1):
#         print(f"  {idx}. ID: {p.get('property_id')} | Title: {p.get('title')}")
#         print(f"     💰 السعر: {p.get('price'):,} ج.م | 🛏️ الغرف: {p.get('pf_bedrooms')} | 📐 المساحة: {p.get('pf_area_sqm')} م² | 📍 الموقع: {p.get('location')}\n")

#     print("\n----------------------------------------")
#     print("🧪 Test 2: Fallback Trigger Search")
#     res2 = matcher.search_properties(test_case_impossible_rooms)
#     print(f"✅ Total Found: {res2['total_found']} | Fallback Used: {res2['used_fallback']}")
#     print("🏠 [نتائج Test 2 (Fallback)]:")
#     for idx, p in enumerate(res2['properties'], 1):
#         print(f"  {idx}. ID: {p.get('property_id')} | Title: {p.get('title')}")
#         print(f"     💰 السعر: {p.get('price'):,} ج.م | 🛏️ الغرف: {p.get('pf_bedrooms')} | 📐 المساحة: {p.get('pf_area_sqm')} م² | 📍 الموقع: {p.get('location')}\n")