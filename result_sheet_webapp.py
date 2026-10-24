"""
Result Sheet Web Application & PDF Generator
============================================
Features:
- Institution Name, Class, Exam Type, Month/Year configuration
- Subject-wise Mark Entry workflow (Select subject -> Enter marks for student list)
- Edit mark functionality
- Ranking / Roll Determination Logic:
  1. Total Mark (Descending)
  2. Tie-breaker 1: Highest Bangla mark
  3. Tie-breaker 2: Highest English mark
  4. Tie-breaker 3: Original roll (Ascending)
- Percentage calculation based on total marks
- Page limit rule: Max 30 students per page (Page 2 header: "Result Sheet - 2")
- PDF Download matching original Result Sheet format
"""

import streamlit as st
import pandas as pd
import io
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Result Sheet Generator", layout="wide")

# Session State Initialization
if "institution_name" not in st.session_state:
    st.session_state["institution_name"] = "রংধনু শিক্ষাগৃহ"
if "est_year" not in st.session_state:
    st.session_state["est_year"] = "স্থাপিত : ২০১৬"
if "exam_title" not in st.session_state:
    st.session_state["exam_title"] = "মাসিক মূল্যয়ন ও রোল নির্ধারনী পরিক্ষা - অক্টোবর/২০২৬"
if "class_name" not in st.session_state:
    st.session_state["class_name"] = "Class : 10 (Science)"
if "teacher_name" not in st.session_state:
    st.session_state["teacher_name"] = "Nonigopal Ray"
if "max_marks_total" not in st.session_state:
    st.session_state["max_marks_total"] = 600

if "subjects" not in st.session_state:
    st.session_state["subjects"] = ["Bangla 2nd", "English 1st", "English 2nd", "ICT", "Math", "Physics", "BGS"]

if "students" not in st.session_state:
    # Pre-populate sample students
    st.session_state["students"] = [
        {"old_roll": 1, "name": "নয়ন ইসলাম", "marks": {"Bangla 2nd": 80, "English 1st": 56, "English 2nd": 66, "ICT": 21, "Math": 63, "Physics": 64, "BGS": 75}},
        {"old_roll": 2, "name": "বিকাশ রায়", "marks": {"Bangla 2nd": 74, "English 1st": 58, "English 2nd": 66, "ICT": 13, "Math": 58, "Physics": 60, "BGS": 70}},
        {"old_roll": 3, "name": "ওহি মনি", "marks": {"Bangla 2nd": 60, "English 1st": 69, "English 2nd": 66, "ICT": 21, "Math": 38, "Physics": 55, "BGS": 43}},
        {"old_roll": 4, "name": "জেমি আক্তার", "marks": {"Bangla 2nd": "-", "English 1st": "-", "English 2nd": "-", "ICT": "-", "Math": "-", "Physics": "-", "BGS": "-"}},
        {"old_roll": 5, "name": "রাব্বি", "marks": {"Bangla 2nd": 61, "English 1st": 45, "English 2nd": 54, "ICT": 18, "Math": 41, "Physics": 48, "BGS": 34}},
        {"old_roll": 6, "name": "সাথি রায়", "marks": {"Bangla 2nd": 57, "English 1st": 48, "English 2nd": 50, "ICT": 18, "Math": 31, "Physics": 42, "BGS": 50}},
        {"old_roll": 7, "name": "মিষ্টি আক্তার", "marks": {"Bangla 2nd": 41, "English 1st": 26, "English 2nd": 14, "ICT": 13, "Math": 13, "Physics": 33, "BGS": 44}}
    ]

# Navigation Sidebar
st.sidebar.title("রংধনু রেজাল্ট শিট সিস্টেম")
menu = st.sidebar.radio("মেনি সেকশন:", ["১. সেটিংস ও বিষয় নির্বাচন", "২. বিষয়ভিত্তিক নম্বর এন্ট্রি ও এডিট", "৩. রেজাল্ট শিট ভিউ ও র‍্যাঙ্কিং", "৪. PDF ডাউনলোড"])

# --- SECTION 1: Settings ---
if menu == "১. সেটিংস ও বিষয় নির্বাচন":
    st.header("⚙️ প্রতিষ্ঠানের নাম ও পরীক্ষার তথ্য সেটিংস")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state["institution_name"] = st.text_input("প্রতিষ্ঠানের নাম (Header):", st.session_state["institution_name"])
        st.session_state["est_year"] = st.text_input("স্থাপিত বছর:", st.session_state["est_year"])
        st.session_state["exam_title"] = st.text_input("পরীক্ষার ধরন ও মাস/বছর:", st.session_state["exam_title"])
    with col2:
        st.session_state["class_name"] = st.text_input("শ্রেণি ও বিভাগ (Class & Section):", st.session_state["class_name"])
        st.session_state["teacher_name"] = st.text_input("দায়িত্বরত শিক্ষকের নাম:", st.session_state["teacher_name"])
        st.session_state["max_marks_total"] = st.number_input("সর্বমোট নম্বর (Percentage হিসেবের জন্য):", value=st.session_state["max_marks_total"])

    st.subheader("📚 বিষয় তালিকা (Subjects List)")
    subs_text = st.text_area("বিষয়সমূহ (কমা দিয়ে আলাদা করুন):", value=", ".join(st.session_state["subjects"]))
    st.session_state["subjects"] = [s.strip() for s in subs_text.split(",") if s.strip()]

    st.subheader("👥 শিক্ষার্থী যোগ করুন")
    with st.form("add_student_form"):
        new_roll = st.number_input("শিক্ষার্থীর রোল:", min_value=1, step=1)
        new_name = st.text_input("শিক্ষার্থীর নাম (বাংলায়):")
        submitted = st.form_submit_button("শিক্ষার্থী যুক্ত করুন")
        if submitted and new_name:
            # Check if student exists
            st.session_state["students"].append({
                "old_roll": int(new_roll),
                "name": new_name,
                "marks": {s: "-" for s in st.session_state["subjects"]}
            })
            st.success(f"শিক্ষার্থী '{new_name}' (রোল {new_roll}) সফলভাবে যুক্ত হয়েছে!")

# --- SECTION 2: Subject-wise Mark Entry ---
elif menu == "২. বিষয়ভিত্তিক নম্বর এন্ট্রি ও এডিট":
    st.header("📝 বিষয়ভিত্তিক নম্বর এন্ট্রি")
    if not st.session_state["subjects"]:
        st.warning("আগে সেটিংস থেকে বিষয় যুক্ত করুন।")
    else:
        selected_sub = st.selectbox("বিষয় নির্বাচন করুন (Select Subject):", st.session_state["subjects"])
        st.info(f"বর্তমান বিষয়: **{selected_sub}** | মোট শিক্ষার্থী: {len(st.session_state['students'])}")

        st.subheader("শিক্ষার্থীদের মার্কস এন্ট্রি / এডিট ফরম:")
        with st.form("marks_entry_form"):
            updated_marks = {}
            for idx, student in enumerate(st.session_state["students"]):
                col_r, col_n, col_m = st.columns([1, 3, 2])
                col_r.write(f"**রোল: {student['old_roll']}**")
                col_n.write(f"**{student['name']}**")
                curr_val = str(student["marks"].get(selected_sub, "-"))
                val_input = col_m.text_input(f"Mark ({student['name']})", value=curr_val, key=f"m_{selected_sub}_{student['old_roll']}")
                updated_marks[student["old_roll"]] = val_input

            save_btn = st.form_submit_button("💾 এই বিষয়ের নম্বর সংরক্ষণ করুন")
            if save_btn:
                for student in st.session_state["students"]:
                    roll = student["old_roll"]
                    val = updated_marks[roll].strip()
                    if val.isdigit():
                        student["marks"][selected_sub] = int(val)
                    elif val == "" or val == "-":
                        student["marks"][selected_sub] = "-"
                    else:
                        try:
                            student["marks"][selected_sub] = float(val)
                        except ValueError:
                            student["marks"][selected_sub] = "-"
                st.success(f"'{selected_sub}' বিষয়ের নম্বর সফলভাবে সংরক্ষিত হয়েছে!")

# --- SECTION 3: Result Sheet & Ranking Calculation ---
elif menu == "৩. রেজাল্ট শিট ভিউ ও র‍্যাঙ্কিং":
    st.header("📊 রেজাল্ট শিট ও নতুন রোল র‍্যাঙ্কিং")

    # Ranking logic
    def compute_ranks(students, subjects, max_total):
        processed = []
        for s in students:
            tot = 0
            bangla_tot = 0
            english_tot = 0
            for sub in subjects:
                m = s["marks"].get(sub, "-")
                if isinstance(m, (int, float)):
                    tot += m
                    if "Bangla" in sub or "বাংলা" in sub:
                        bangla_tot += m
                    elif "English" in sub or "ইংরেজি" in sub:
                        english_tot += m

            pct = (tot / max_total * 100) if max_total > 0 else 0
            processed.append({
                "old_roll": s["old_roll"],
                "name": s["name"],
                "marks": s["marks"],
                "total": tot,
                "bangla_tot": bangla_tot,
                "english_tot": english_tot,
                "percentage": pct
            })

        # Sorting: Total desc, Bangla desc, English desc, Old roll asc
        sorted_list = sorted(processed, key=lambda x: (-x["total"], -x["bangla_tot"], -x["english_tot"], x["old_roll"]))
        for rank, item in enumerate(sorted_list, start=1):
            item["new_roll"] = rank
        return sorted_list

    ranked_students = compute_ranks(st.session_state["students"], st.session_state["subjects"], st.session_state["max_marks_total"])

    # Create Display Table DataFrame
    rows = []
    for s in ranked_students:
        r_dict = {"Roll": s["old_roll"], "Name": s["name"]}
        for sub in st.session_state["subjects"]:
            r_dict[sub] = s["marks"].get(sub, "-")
        r_dict["Total"] = s["total"]
        r_dict["Percentage"] = f"{s['percentage']:.1f}%"
        r_dict["New Roll"] = s["new_roll"]
        rows.append(r_dict)

    df_result = pd.DataFrame(rows)
    st.dataframe(df_result, use_container_width=True)

# --- SECTION 4: PDF Download ---
elif menu == "৪. PDF ডাউনলোড":
    st.header("📄 রেজাল্ট শিট PDF তৈরি ও ডাউনলোড")
    st.write("আপনার আপলোড করা প্রাতিষ্ঠানিক ডিজাইনের হুবহু PDF আউটপুট তৈরি করতে নিচের বোতামে চাপুন।")

    # PDF Draw Function with multi-page pagination (30 students max per page)
    def generate_pdf_bytes():
        # Function to compute ranks
        def compute_ranks(students, subjects, max_total):
            processed = []
            for s in students:
                tot = 0
                bangla_tot = 0
                english_tot = 0
                for sub in subjects:
                    m = s["marks"].get(sub, "-")
                    if isinstance(m, (int, float)):
                        tot += m
                        if "Bangla" in sub or "বাংলা" in sub:
                            bangla_tot += m
                        elif "English" in sub or "ইংরেজি" in sub:
                            english_tot += m

                pct = (tot / max_total * 100) if max_total > 0 else 0
                processed.append({
                    "old_roll": s["old_roll"],
                    "name": s["name"],
                    "marks": s["marks"],
                    "total": tot,
                    "bangla_tot": bangla_tot,
                    "english_tot": english_tot,
                    "percentage": pct
                })

            sorted_list = sorted(processed, key=lambda x: (-x["total"], -x["bangla_tot"], -x["english_tot"], x["old_roll"]))
            for rank, item in enumerate(sorted_list, start=1):
                item["new_roll"] = rank
            return sorted_list

        ranked_students = compute_ranks(st.session_state["students"], st.session_state["subjects"], st.session_state["max_marks_total"])

        # Page split (max 30 per page)
        chunk_size = 30
        student_chunks = [ranked_students[i:i + chunk_size] for i in range(0, len(ranked_students), chunk_size)]
        if not student_chunks:
            student_chunks = [[]]

        pdf_pages = []
        bengali_font_path = '/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf'
        bengali_bold_path = '/usr/share/fonts/truetype/noto/NotoSansBengali-Bold.ttf'
        serif_bold_path = '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'
        sans_bold_path = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
        sans_reg_path = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'

        for p_idx, chunk in enumerate(student_chunks, start=1):
            W, H = 2338, 1654
            img = Image.new('RGB', (W, H), color='white')
            draw = ImageDraw.Draw(img)

            font_title = ImageFont.truetype(bengali_bold_path, 68)
            font_est = ImageFont.truetype(bengali_font_path, 28)
            font_exam = ImageFont.truetype(bengali_bold_path, 32)
            font_res_header = ImageFont.truetype(serif_bold_path, 42)
            font_class = ImageFont.truetype(sans_bold_path, 32)
            font_table_hdr = ImageFont.truetype(sans_bold_path, 26)
            font_table_cell_bn = ImageFont.truetype(bengali_font_path, 26)
            font_table_cell_en = ImageFont.truetype(sans_reg_path, 26)
            font_teacher_name = ImageFont.truetype(sans_bold_path, 28)
            font_teacher_label = ImageFont.truetype(bengali_bold_path, 28)

            y = 70
            title_text = st.session_state["institution_name"]
            res_sheet_title = "Result Sheet" if p_idx == 1 else f"Result Sheet - {p_idx}"

            # Title
            bbox = draw.textbbox((0, 0), title_text, font=font_title)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) / 2, y), title_text, font=font_title, fill='black')
            y += 85

            # Est
            bbox = draw.textbbox((0, 0), st.session_state["est_year"], font=font_est)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) / 2, y), st.session_state["est_year"], font=font_est, fill='black')
            y += 45

            # Exam Title
            bbox = draw.textbbox((0, 0), st.session_state["exam_title"], font=font_exam)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) / 2, y), st.session_state["exam_title"], font=font_exam, fill='black')
            y += 65

            # Result Sheet Title
            bbox = draw.textbbox((0, 0), res_sheet_title, font=font_res_header)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) / 2, y), res_sheet_title, font=font_res_header, fill='black')
            y += 75

            # Class line
            margin_x = 100
            draw.text((margin_x, y), st.session_state["class_name"], font=font_class, fill='black')
            y += 55

            # Table calculation
            table_x1, table_x2 = margin_x, W - margin_x
            table_w = table_x2 - table_x1
            roll_w, name_w, total_w, pct_w, new_roll_w = 110, 340, 130, 190, 140
            num_subs = len(st.session_state["subjects"])
            rem_w = table_w - (roll_w + name_w + total_w + pct_w + new_roll_w)
            sub_w = rem_w / num_subs if num_subs > 0 else 100

            col_widths = [roll_w, name_w] + [sub_w]*num_subs + [total_w, pct_w, new_roll_w]
            col_headers = ["Roll", "Name"] + st.session_state["subjects"] + ["Total", "Percentage", "New Roll"]

            col_xs = [table_x1]
            curr_x = table_x1
            for w in col_widths:
                curr_x += w
                col_xs.append(curr_x)

            row_h = 38 if len(chunk) > 15 else 52
            header_y1, header_y2 = y, y + row_h

            draw.rectangle([table_x1, header_y1, table_x2, header_y2], outline='black', width=2)
            for i, hdr in enumerate(col_headers):
                x1, x2 = col_xs[i], col_xs[i+1]
                bbox = draw.textbbox((0, 0), hdr, font=font_table_hdr)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                draw.text((x1 + (x2 - x1 - tw)/2, header_y1 + (row_h - th)/2 - 2), hdr, font=font_table_hdr, fill='black')
                draw.line([x2, header_y1, x2, header_y2], fill='black', width=2)

            y = header_y2
            for student in chunk:
                ry1, ry2 = y, y + row_h
                draw.rectangle([table_x1, ry1, table_x2, ry2], outline='black', width=1)
                row_vals = [str(student['old_roll']), student['name']] + [str(student['marks'].get(s, '-')) for s in st.session_state["subjects"]] + [str(student['total']), f"{student['percentage']:.1f}%", str(student['new_roll'])]

                for i, val in enumerate(row_vals):
                    x1, x2 = col_xs[i], col_xs[i+1]
                    f_cell = font_table_cell_bn if i == 1 else font_table_cell_en
                    bbox = draw.textbbox((0, 0), val, font=f_cell)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    cx = x1 + 20 if i == 1 else x1 + (x2 - x1 - tw)/2
                    draw.text((cx, ry1 + (row_h - th)/2 - 3), val, font=f_cell, fill='black')
                    draw.line([x2, ry1, x2, ry2], fill='black', width=1)
                y = ry2

            draw.rectangle([table_x1, header_y1, table_x2, y], outline='black', width=2)

            # Footer
            footer_y = H - 140
            teacher_x2, teacher_x1 = table_x2, table_x2 - 350
            if st.session_state["teacher_name"]:
                bbox = draw.textbbox((0, 0), st.session_state["teacher_name"], font=font_teacher_name)
                tw = bbox[2] - bbox[0]
                draw.text((teacher_x1 + (350 - tw)/2, footer_y), st.session_state["teacher_name"], font=font_teacher_name, fill='black')

            t_label = "দায়িত্বরত শিক্ষক"
            bbox = draw.textbbox((0, 0), t_label, font=font_teacher_label)
            tw = bbox[2] - bbox[0]
            draw.text((teacher_x1 + (350 - tw)/2, footer_y + 40), t_label, font=font_teacher_label, fill='black')

            pdf_pages.append(img)

        pdf_bytes = io.BytesIO()
        if pdf_pages:
            pdf_pages[0].save(pdf_bytes, format='PDF', save_all=True, append_images=pdf_pages[1:], resolution=200.0)
        return pdf_bytes.getvalue()

    pdf_data = generate_pdf_bytes()
    st.download_button(
        label="📥 প্রাতিষ্ঠানিক রেজাল্ট শিট (PDF) ডাউনলোড করুন",
        data=pdf_data,
        file_name="Result_Sheet_Class10_October2026.pdf",
        mime="application/pdf"
    )
