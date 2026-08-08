from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ==================================
# 添加衣服 Schema
# ==================================
class WardrobeCreate(BaseModel):
    image_path: Optional[str] = None
    recognition_status: Optional[str] = "manual"
    # ==========================
    # 基础信息
    # ==========================
    # 衣服名称
    # 示例:
    # 白色T恤
    name: str
    # 分类
    # 示例:
    # 上衣
    # 裤子
    category: str
    # ==========================
    # 旧字段
    # 保留兼容 V4.3
    # ==========================
    # 颜色
    # 示例:
    # 白色
    color: str
    # 风格
    # 示例:
    # 日系简约
    style: str
    # 季节
    # 示例:
    # 春季
    season: str
    # ==========================
    # V4.4 新增标签
    # ==========================
    # 颜色标签
    # 示例:
    #
    # [
    # "白色",
    # "基础色"
    # ]
    color_tags: List[str] = Field(default_factory=list)
    # 风格标签
    # 示例:
    #
    # [
    # "日系简约",
    # "休闲"
    # ]
    style_tags: List[str] = Field(default_factory=list)
    # 版型标签
    # 示例:
    #
    # [
    # "宽松",
    # "基础款"
    # ]
    fit_tags: List[str] = Field(default_factory=list)
    occasion_tags: List[str] = Field(default_factory=list)

# ==================================
# 返回衣服数据
# ==================================
class WardrobeResponse(BaseModel):
    id: int
    image_path: Optional[str] = None
    recognition_status: Optional[str] = None
    name: str
    category: str
    color: str
    season: str
    style: str
    color_tags: List[str]
    style_tags: List[str]
    fit_tags: List[str]
    occasion_tags: List[str]
    model_config = ConfigDict(from_attributes=True)

    @field_validator(
        "color_tags",
        "style_tags",
        "fit_tags",
        "occasion_tags",
        mode="before",
    )
    @classmethod
    def ensure_list(cls, value):
        return value or []


class ClothingAnalyzeResponse(BaseModel):
    name: str
    category: str
    color: str
    style: str
    season: str
    color_tags: List[str]
    style_tags: List[str]
    fit_tags: List[str]
    occasion_tags: List[str]
    image_path: str
    recognition_status: str
