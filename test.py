import streamlit as st
from pymongo import MongoClient
import os

def get_secret(key):
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except:
        pass
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return os.getenv(key)
    except:
        pass
    
    return None

@st.cache_resource
def test_mongo():
    try:
        uri = get_secret("MONGODB_URI")
        if not uri:
            st.error("❌ Không tìm thấy MONGODB_URI")
            return False
            
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        
        # Test ping
        client.admin.command('ping')
        st.success("✅ Ping thành công!")
        
        # Test truy cập database
        db = client.get_default_database()
        if db is not None:
            st.write(f"✅ Database: {db.name}")
        else:
            st.warning("⚠️ Không tìm thấy database mặc định")
            # Thử database cụ thể
            db = client["chatcodeai"]
            if db is not None:
                st.write(f"✅ Database: {db.name}")
            else:
                st.error("❌ Không thể truy cập database")

        # Test collection
        try:
            collection = db["normalized"]
            count = collection.estimated_document_count()
            st.write(f"✅ Collection có {count} documents")
        except Exception as e:
            st.error(f"❌ Lỗi truy cập collection: {e}")
            # Liệt kê collections
            try:
                collections = db.list_collection_names()
                st.write(f"📚 Các collections có sẵn: {collections}")
            except:
                pass
        
        return True
    except Exception as e:
        st.error(f"❌ Lỗi kết nối MongoDB: {str(e)}")
        return False

# Giao diện Streamlit
st.title("🔍 Test kết nối MongoDB")

uri = get_secret("MONGODB_URI")
if uri:
    st.info("✅ Đã tìm thấy MONGODB_URI")
    st.write("URI (ẩn mật khẩu):", uri.split("@")[0] + "@****")
else:
    st.error("❌ Không tìm thấy MONGODB_URI")

if st.button("🧪 Test kết nối MongoDB"):
    test_mongo()