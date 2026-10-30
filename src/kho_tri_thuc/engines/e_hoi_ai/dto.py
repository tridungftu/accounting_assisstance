"""DTO gốc của cổng AI dùng chung, tái xuất cho engine e_hoi_ai.

AI-1a chỉ giữ nguyên các lớp hiện có; schema đầu vào và cờ chỉ Local
thuộc AI-1b. Module này không tạo cổng, provider hoặc kết nối CSDL.
"""

from kho_tri_thuc.tri_thuc.cong_ai import KetQuaAI, TruongAI, YeuCauAI

__all__ = ["YeuCauAI", "TruongAI", "KetQuaAI"]
