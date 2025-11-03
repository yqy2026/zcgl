from typing import Any
"""
印章和手写体识别服务
专门识别合同中的红色印章、签名和手写文字
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum


import cv2
import numpy as np
import pytesseract
from skimage.transform import resize

logger = logging.getLogger(__name__)


class SealType(str, Enum):
    """印章类型"""

    RED_CIRCLE_SEAL = "red_circle"  # 红色圆形印章
    SQUARE_SEAL = "square_seal"  # 方形印章
    RECTANGLE_SEAL = "rectangle_seal"  # 矩形印章
    OVAL_SEAL = "oval_seal"  # 椭圆形印章
    STAR_SEAL = "star_seal"  # 星形印章
    SIGNATURE = "signature"  # 签名
    ELECTRONIC_SEAL = "electronic_seal"  # 电子印章


@dataclass
class DetectionResult:
    """检测结果"""

    x: int
    y: int
    width: int
    height: int
    confidence: float
    seal_type: SealType
    text_content: str | None = None
    bbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    metadata: dict[str, Any] = None


@dataclass
class SealInfo:
    """印章信息"""

    seal_type: SealType
    position: str
    confidence: float
    text_extracted: str | None = None
    validated: bool = False
    color_info: dict[str, Any] | None = None
    obstruction_areas: list[dict[str, Any]] = []


class SealDetector:
    """印章检测器"""

    def __init__(self):
        self.red_seal_templates = self._load_red_seal_templates()
        self.signatures_patterns = self._load_signature_patterns()

    def _load_red_seal_templates(self) -> list[dict[str, Any]]:
        """加载红色印章模板"""
        return [
            {
                "name": "standard_circle",
                "shape": "circle",
                "expected_radius_ratio": 1.0,
                "min_radius": 15,
                "max_radius": 40,
                "color_hsv_range": {
                    "hue_low": 0,
                    "hue_high": 10,
                    "saturation_low": 100,
                    "saturation_high": 255,
                },
            },
            {
                "name": "government_seal",
                "shape": "circle",
                "expected_radius_ratio": 1.0,
                "min_radius": 20,
                "max_radius": 50,
                "color_hsv_range": {
                    "hue_low": 0,
                    "hue_high": 20,
                    "saturation_low": 150,
                    "saturation_high": 255,
                },
                "center_text_patterns": ["XX人民政府", "XX合同专用章", "XX公安局"],
            },
            {
                "name": "corporate_seal",
                "shape": "circle",
                "expected_radius_ratio": 1.0,
                "min_radius": 15,
                "max_radius": 35,
                "color_hsv_range": {
                    "hue_low": 0,
                    "hue_high": 10,
                    "saturation_low": 100,
                    "saturation_high": 255,
                },
            },
            {
                "name": "oval_seal",
                "shape": "ellipse",
                "expected_aspect_ratio_range": (0.7, 1.3),
                "min_radius": 10,
                "max_radius": 30,
            },
        ]

    def _load_signature_patterns(self) -> list[dict[str, Any]]:
        """加载签名模式"""
        return [
            {
                "type": "handwritten_signature",
                "name": "自由签名",
                "expected_strokes": list(range(3, 20)),
                "connected_components": list(range(2, 15)),
                "aspect_ratio_range": (0.1, 0.3),
                "line_thickness_range": (1, 4),
            },
            {
                "type": "printed_signature",
                "name": "印刷签名",
                "expected_strokes": list(range(2, 8)),
                "connected_components": 1,
                "aspect_ratio_range": (0.3, 0.8),
                "line_thickness_range": (2, 6),
            },
            {
                "type": "chinese_character_signature",
                "name": "汉字签名",
                "expected_strokes": list(range(5, 30)),
                "character_count_range": (1, 4),
                "line_thickness_range": (2, 5),
            },
        ]

    async def detect_seals(self, image_path: str) -> list[DetectionResult]:
        """检测图像中的印章和签名"""
        try:
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"无法读取图像: {image_path}")
                return []

            # 图像预处理
            processed_image = self._preprocess_seal_image(image)

            # 检测红色印章
            red_seals = await self._detect_red_seals(processed_image)

            # 检测签名
            signatures = await self._detect_signatures(processed_image)

            # 合并结果
            all_detections = red_seals + signatures

            logger.info(f"检测到{len(all_detections)}个印章/签名")
            return all_detections

        except Exception as e:
            logger.error(f"印章检测失败: {e}")
            return []

    def _preprocess_seal_image(self, image: np.ndarray) -> np.ndarray:
        """印章识别图像预处理"""
        # 增强红色通道
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 分离红色通道
        h, s, v = cv2.split(hsv)

        # 创建红色掩码
        lower_red = np.array([0, 120, 100])
        upper_red = np.array([10, 255, 255])

        # 增强红色区域
        red_mask = cv2.inRange(hsv, lower_red, upper_red)

        # 形态学闭操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5), 2)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)

        # 应用红色掩码
        red_enhanced = cv2.bitwise_and(image, image, mask=red_mask)

        # 去噪处理
        denoised = cv2.bilateralFilter(red_enhanced, 20, 80, 75)

        # 转换为灰度图
        gray = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)

        # CLAHE增强
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        return enhanced

    async def _detect_red_seals(self, image: np.ndarray) -> list[DetectionResult]:
        """检测红色印章"""
        try:
            # 转换为HSV色彩空间
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)

            detections = []

            # 应用所有印章模板
            for template in self.red_seal_templates:
                template_detections = self._apply_seal_template(hsv, template)
                detections.extend(template_detections)

            # 聚类检测（去除重叠）
            filtered_detections = self._filter_seal_detections(detections)

            logger.info(f"检测到{len(filtered_detections)}个红色印章")
            return filtered_detections

        except Exception as e:
            logger.error(f"红色印章检测失败: {e}")
            return []

    def _apply_seal_template(
        self, hsv_image: np.ndarray, template: dict[str, Any]
    ) -> list[DetectionResult]:
        """应用单个印章模板"""
        detections = []

        if template["shape"] == "circle":
            detections.extend(self._detect_circular_seals(hsv_image, template))
        elif template["shape"] == "ellipse":
            detections.extend(self._detect_elliptical_seals(hsv_image, template))
        else:
            # 默认圆形检测
            detections.extend(self._detect_circular_seals(hsv_image, template))

        return detections

    def _detect_circular_seals(
        self, hsv_image: np.ndarray, template: dict[str, Any]
    ) -> list[DetectionResult]:
        """检测圆形印章"""
        detections = []
        try:
            # 转换为二值图像
            _, mask = cv2.threshold(hsv_image[:, :, 2], 127, 255, cv2.THRESH_BINARY)

            # 查找圆形
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            min_radius = template["min_radius"]
            max_radius = template["max_radius"]
            expected_ratio = template.get("expected_radius_ratio", 1.0)
            color_range = template["color_hsv_range"]

            # 颜色分割
            lower_red = np.array(
                [color_range["hue_low"], color_range["saturation_low"], 50]
            )
            upper_red = np.array(
                [color_range["hue_high"], color_range["saturation_high"], 255]
            )
            cv2.inRange(hsv_image, lower_red, upper_red)  # 预留字段，当前未使用

            for contour in contours:
                # 过滤轮廓
                area = cv2.contourArea(contour)
                if area < min_radius * min_radius * 3.14:  # 太小的圆
                    continue

                # 查找最小包围圆
                (x, y), radius = cv2.minEnclosingCircle(contour)
                if radius < min_radius or radius > max_radius:
                    continue

                # 检查圆度比例
                (center_x, center_y), radius_actual = cv2.minEnclosingCircle(contour)
                actual_ratio = radius_actual / radius
                if (
                    actual_ratio < expected_ratio * 0.7
                    or actual_ratio > expected_ratio * 1.3
                ):
                    continue

                # 检查是否主要为红色
                if self._is_dominantly_red(mask, x, y, radius):
                    detection = DetectionResult(
                        x=center_x,
                        y=center_y,
                        width=radius_actual * 2,
                        height=radius_actual * 2,
                        confidence=self._calculate_seal_confidence(
                            area, radius_actual, template
                        ),
                        seal_type=SealType.RED_CIRCLE_SEAL,
                        bbox=(
                            center_x - radius_actual,
                            center_y - radius_actual,
                            center_x + radius_actual,
                            center_y + radius_actual,
                        ),
                    )

                    # 尝试OCR识别印章文字
                    if template.get("center_text_patterns"):
                        text = self._extract_seal_text(
                            hsv_image[y - radius : y + radius, x - radius : x + radius],
                            templates=template["center_text_patterns"],
                        )
                        detection.text_content = text
                        detection.validated = self._validate_seal_text(text, template)

                    detections.append(detection)

            return detections

        except Exception as e:
            logger.error(f"圆形印章检测失败: {e}")
            return []

    def _detect_elliptical_seals(
        self, hsv_image: np.ndarray, template: dict[str, Any]
    ) -> list[DetectionResult]:
        """检测椭圆形印章"""
        detections = []
        try:
            _, mask = cv2.threshold(hsv_image[:, :, 2], 127, 255, cv2.THRESH_BINARY)

            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            min_radius = template["min_radius"]
            max_radius = template["max_radius"]
            aspect_ratio_range = template.get("aspect_ratio_range", (0.5, 2.0))

            for contour in contours:
                area = cv2.contourArea(contour)
                if area < min_radius * min_radius * 3.14:
                    continue

                if len(contour) < 5:  # 椭圆需要至少5个点
                    continue

                # 拟合椭圆
                ellipse = cv2.fitEllipse(contour)

                # 检查长轴和短轴比例
                major_axis = max(ellipse[1], ellipse[3])
                minor_axis = min(ellipse[1], ellipse[3])
                actual_ratio = major_axis / minor_axis if minor_axis > 0 else 1.0

                if not (aspect_ratio_range[0] <= actual_ratio <= aspect_ratio_range[1]):
                    continue

                # 估算半径
                radius_est = (major_axis + minor_axis) / 4

                if radius_est < min_radius or radius_est > max_radius:
                    continue

                detection = DetectionResult(
                    x=int(ellipse[0][0]),
                    y=int(ellipse[0][1]),
                    width=int(ellipse[1][0]),
                    height=int(ellipse[1][1]),
                    confidence=self._calculate_seal_confidence(
                        area, radius_est, template, "ellipse"
                    ),
                    seal_type=SealType.OVAL_SEAL,
                    bbox=(
                        int(ellipse[0][0]),
                        int(ellipse[0][1]),
                        int(ellipse[0][0]) + int(ellipse[1][0]),
                        int(ellipse[0][1]) + int(ellipse[1][0]),
                    ),
                )

                detections.append(detection)

            return detections

        except Exception as e:
            logger.error(f"椭圆形印章检测失败: {e}")
            return []

    def _is_dominantly_red(self, mask: np.ndarray, x: int, y: int, radius: int) -> bool:
        """检查区域是否主要为红色"""
        # 创建圆形采样区域
        center_mask = np.zeros(mask.shape, dtype=np.uint8)
        cv2.circle(center_mask, (x, y), radius, 255, -1)

        # 计算红色像素比例
        total_pixels = np.count_nonzero(
            mask[y - radius : y + radius, x - radius : x + radius]
        )
        red_pixels = np.count_nonzero(
            cv2.bitwise_and(mask, center_mask, mask, center_mask)
        )

        # 如果红色像素超过60%，认为是主要红色
        return red_pixels / total_pixels > 0.6

    def _filter_seal_detections(
        self, detections: list[DetectionResult]
    ) -> list[DetectionResult]:
        """过滤重叠的印章检测结果"""
        if not detections:
            return []

        # 按置信度排序
        detections.sort(key=lambda x: x.confidence, reverse=True)

        filtered_detections = []
        for i, detection in enumerate(detections):
            is_duplicate = False
            for j, other in enumerate(detections):
                if i == j:
                    continue

                # 检查IoU（交并比）
                iou = self._calculate_iou(detection.bbox, other.bbox)
                if iou > 0.7:  # 重叠阈值
                    is_duplicate = True
                    break

            if not is_duplicate:
                filtered_detections.append(detection)

        return filtered_detections

    async def _detect_signatures(self, image: np.ndarray) -> list[DetectionResult]:
        """检测签名"""
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # 边缘检测
            edges = cv2.Canny(gray, 50, 150, apertureSize=3, L2gradient=True)

            # 形态学操作
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3), 1)
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

            # 查找轮廓
            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            signatures = []

            for contour in contours:
                # 过滤小轮廓
                area = cv2.contourArea(contour)
                if area < 1000:  # 最小面积阈值
                    continue

                # 分析轮廓特征
                signature_type = self._classify_signature_type(contour, gray)

                if signature_type:
                    detection = DetectionResult(
                        x=0,
                        y=0,
                        width=0,
                        height=0,
                        confidence=0.0,
                        seal_type=SealType.SIGNATURE,
                        metadata={"type": signature_type},
                    )

                    # 添加边界框
                    x, y, w, h = cv2.boundingRect(contour)
                    detection.x, detection.y, detection.width, detection.height = (
                        x,
                        y,
                        w,
                        h,
                    )

                    # 尝试OCR识别签名文字
                    text = await self._extract_signature_text(
                        image[y : y + h, x : x + w], signature_type=signature_type
                    )
                    detection.text_content = text
                    detection.validated = self._validate_signature_text(text)

                    signatures.append(detection)

            return signatures

        except Exception as e:
            logger.error(f"签名检测失败: {e}")
            return []

    def _classify_signature_type(self, contour, gray: np.ndarray) -> str | None:
        """分类签名类型"""
        # 计算轮廓特征
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)

        if perimeter == 0:
            return None

        circularity = (4 * np.pi * area) / (perimeter * perimeter)

        # 长宽比
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = float(w) / h if h > 0 else 1.0

        # 分析轮廓特征
        if area < 500:
            return None

        if circularity > 0.7 and aspect_ratio < 0.8:
            return "circular_pattern"  # 圆形笔画
        elif 0.1 <= circularity <= 0.4:
            return "irregular_curve"  # 不规则曲线
        elif aspect_ratio > 0.6:
            return "horizontal_stroke"  # 横向笔画
        elif len(contour) < 20:
            return "short_strokes"  # 短笔画
        elif 10 <= len(contour) <= 30:
            return "concentrated_strokes"  # 浓缩笔画
        else:
            return "detailed_signature"  # 详细签名

    async def _extract_seal_text(
        self, image_region: np.ndarray, templates: list[str]
    ) -> str:
        """提取印章文字"""
        try:
            # 使用TesseractOCR
            config = (
                '--psm 7 --oem 3 -c tessedit_char_whitelist 0123456789年月日人民币元角分，。；：""'
                '（）【】《》""'
                "—至起止甲方乙方出租承租法定代表人身份证地址电话金额"
            )
            text = pytesseract.image_to_string(image_region, config=config)

            # 清理和标准化文本
            cleaned_text = self._clean_seal_text(text)

            # 应用模板验证
            for pattern in templates:
                if re.search(pattern, cleaned_text):
                    return cleaned_text

            return cleaned_text

        except Exception as e:
            logger.error(f"印章文字提取失败: {e}")
            return ""

    async def _extract_signature_text(
        self, image_region: np.ndarray, signature_type: str
    ) -> str:
        """提取签名文字"""
        try:
            if signature_type == "printed_signature":
                # 印刷签名使用高分辨率OCR
                scale_factor = 2
            else:
                scale_factor = 1

            # 放大图像以提高OCR质量
            if image_region.shape[1] < 100:
                scale_factor = 3

            resized_image = resize(
                image_region,
                None,
                fx=scale_factor,
                fy=scale_factor,
                interpolation=cv2.INTER_CUBIC,
            )

            # 根据签名类型选择OCR配置
            if signature_type == "chinese_character_signature":
                config = (
                    '--psm 7 --oem 3 -c tessedit_char_whitelist 1234567890号一二三四五六七八九十百千万年月日，。；：""'
                    '（）【】《》""'
                    "—至起止"
                )
            elif signature_type == "detailed_signature":
                config = "--psm 6 --oem 3"
            else:
                config = "--psm 7 --oem 3"

            text = pytesseract.image_to_string(resized_image, config=config)

            return self._clean_signature_text(text)

        except Exception as e:
            logger.error(f"签名文字提取失败: {e}")
            return ""

    def _clean_seal_text(self, text: str) -> str:
        """清理印章文字"""
        # 移除多余的空格和换行
        cleaned = re.sub(r"\s+", " ", text.strip())

        # 标准化常见词汇
        replacements = {
            "人-民-政府": "人民政府",
            "合同专用": "合同专用章",
            "有限责任": "有限公司",
            "股份有限": "股份有限公司",
        }

        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)

        return cleaned.strip()

    def _clean_signature_text(self, text: str) -> str:
        """清理签名文字"""
        # 移除OCR识别错误
        cleaned = re.sub(r"[^\w\u4e00-\u9fff]", "", text.strip())

        # 移除过多的换行
        cleaned = re.sub(r"\n+", " ", cleaned)

        return cleaned.strip()

    def _validate_seal_text(self, text: str, template: dict[str, Any]) -> bool:
        """验证印章文字有效性"""
        if not text or not text.strip():
            return False

        # 对于有特定文字模板的印章
        center_patterns = template.get("center_text_patterns", [])
        for pattern in center_patterns:
            if re.search(pattern, text.strip()):
                return True

        return len(text.strip()) > 1  # 至少要有实际字符

    def _validate_signature_text(self, text: str) -> bool:
        """验证签名文字有效性"""
        if not text or not text.strip():
            return False

        # 签名应该是简短的
        if len(text.strip()) > 20:
            return False

        return len(text.strip()) > 0

    def _calculate_seal_confidence(
        self, area: float, radius: float, template: dict[str, Any], shape: str = None
    ) -> float:
        """计算印章置信度"""
        confidence = 0.0

        # 基于面积
        if area > 5000:  # 较大的印章
            confidence += 0.3
        elif area > 2000:
            confidence += 0.2

        # 基于圆度
        expected_ratio = template.get("expected_radius_ratio", 1.0)
        if shape == "ellipse":
            # 椭圆的长轴短轴比接近1
            pass
        else:
            # 圆形的半径比例
            actual_ratio = radius / radius  # radius应该是已知的，这里简化处理
            if expected_ratio == 1.0:
                confidence += 0.2
            elif abs(actual_ratio - expected_ratio) < 0.1:
                confidence += 0.1

        # 基于模板匹配
        if "center_text_patterns" in template:
            confidence += 0.3

        return min(confidence, 1.0)

    def _extract_seal_text(self, image_region: np.ndarray, templates: list) -> str:
        """提取印章文字"""
        try:
            # 使用OCR提取文字
            import pytesseract

            # 预处理图像以提高OCR准确性
            gray = cv2.cvtColor(image_region, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

            # 使用Tesseract进行OCR
            text = pytesseract.image_to_string(binary, lang="chi_sim")

            return text.strip()
        except Exception as e:
            logger.warning(f"OCR文字提取失败: {e}")
            return ""

    def _validate_seal_text(self, text: str, template: dict) -> bool:
        """验证印章文字是否符合模板要求"""
        if not text:
            return False

        # 检查是否包含预期的文字模式
        if "center_text_patterns" in template:
            patterns = template["center_text_patterns"]
            for pattern in patterns:
                if pattern in text:
                    return True

        return False


# 全局印章检测器实例
seal_detector = SealDetector()
