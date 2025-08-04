from enum import Enum


class DEPLOYED_APP_STATUS(Enum):
    active = (0, "Đang chạy")
    add_txt = (1, "Đã xác minh TXT")
    deploying = (2, "Đang deploy")
    pending = (3, "Đang chờ")
    inactive = (4, "Đã dừng")
    failed = (99, "Lỗi")  # lỗi cho xuống cuối cùng (order cao)
    removing = (100, "Đang xóa")  # lỗi/xóa luôn cuối bảng

    def __init__(self, order, label):
        self.order = order
        self.label = label

    @property
    def value(self):
        return self.name
