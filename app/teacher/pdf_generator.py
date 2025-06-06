from flask import make_response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
from datetime import datetime
import os

# 日本語フォントの設定（CIDフォントを使用）
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))

FONT_NAME = 'HeiseiMin-W3'  # 明朝体
FONT_NAME_BOLD = 'HeiseiKakuGo-W5'  # ゴシック体

def generate_student_report_pdf(student, class_obj, activities, chat_histories, theme, ai_summary):
    """学生の活動報告PDFを生成"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
    story = []
    
    # スタイルの設定
    styles = getSampleStyleSheet()
    
    # 日本語フォントを使用するスタイル
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=FONT_NAME_BOLD,
        fontSize=20,
        textColor=colors.HexColor('#0056b3'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=FONT_NAME_BOLD,
        fontSize=14,
        textColor=colors.HexColor('#0056b3'),
        spaceBefore=12,
        spaceAfter=6
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14
    )
    
    # タイトル
    story.append(Paragraph("探究活動報告書", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # 基本情報テーブル
    info_data = [
        ['生徒名:', student.username],
        ['クラス:', class_obj.name],
        ['探究テーマ:', theme.title if theme else '未設定'],
        ['作成日:', datetime.now().strftime('%Y年%m月%d日')]
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*inch))
    
    # AI要約セクション
    story.append(Paragraph("1. 活動の要約（AI分析）", heading_style))
    story.append(Paragraph(ai_summary or "要約を生成中にエラーが発生しました。", normal_style))
    story.append(Spacer(1, 0.3*inch))
    
    # 活動記録セクション
    story.append(Paragraph("2. 活動記録", heading_style))
    if activities:
        for i, activity in enumerate(activities[:20]):  # 最新20件
            date_str = activity.timestamp.strftime('%Y/%m/%d %H:%M')
            story.append(Paragraph(f"【{i+1}. {date_str}】", normal_style))
            story.append(Paragraph(activity.content or "内容なし", normal_style))
            if activity.reflection:
                story.append(Paragraph(f"振り返り: {activity.reflection}", normal_style))
            story.append(Spacer(1, 0.2*inch))
    else:
        story.append(Paragraph("活動記録がありません。", normal_style))
    
    # 新しいページ
    if chat_histories:
        story.append(PageBreak())
        
        # チャット履歴セクション
        story.append(Paragraph("3. AIチャットでの学習履歴（抜粋）", heading_style))
        chat_count = 0
        for chat in chat_histories[:30]:  # 最新30件
            if chat.is_user:
                story.append(Paragraph(f"生徒: {chat.message}", normal_style))
            else:
                # AI応答は200文字まで
                message = chat.message[:200] + "..." if len(chat.message) > 200 else chat.message
                story.append(Paragraph(f"AI: {message}", normal_style))
            story.append(Spacer(1, 0.1*inch))
            chat_count += 1
            if chat_count >= 15:  # 1ページに収まる量に制限
                break
    
    # フッター情報
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("※ このレポートは自動生成されたものです。", normal_style))
    
    # PDFを生成
    doc.build(story)
    buffer.seek(0)
    return buffer