import os
from datetime import datetime, timezone
from fpdf import FPDF
from io import BytesIO


class AegisReport(FPDF):
    def __init__(self, scan_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scan_id = scan_id
        self.generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        self.logo_path = "/Users/enzogaggiotti/Documents/Epitech/EIP/Aegis AI/Repository/Aegis-AI-Brain/logo/logo.svg"

    def header(self):
        if self.page_no() > 1:
            self.set_font("helvetica", "I", 8)
            self.set_text_color(128)
            self.cell(
                0, 10, f"Aegis AI - Scan Report {self.scan_id}", border=0, align="L"
            )
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def cover_page(self):
        self.add_page()
        # Aegis AI Branding
        if os.path.exists(self.logo_path):
            try:
                # Centering a 40mm wide logo
                self.image(self.logo_path, x=85, y=20, w=40)
            except Exception as e:
                print(f"Warning: Could not draw logo: {e}")

        self.set_y(60)
        self.set_font("helvetica", "B", 40)
        self.set_text_color(33, 37, 41)
        self.cell(0, 20, "AEGIS AI", align="C", ln=True)

        self.set_font("helvetica", "", 24)
        self.cell(0, 20, "Vulnerability Assessment Report", align="C", ln=True)

        self.ln(40)
        self.set_font("helvetica", "B", 14)
        self.cell(0, 10, f"Scan ID: {self.scan_id}", align="C", ln=True)
        self.set_font("helvetica", "", 12)
        self.cell(0, 10, f"Generated on: {self.generated_at}", align="C", ln=True)

        self.set_y(-60)
        self.set_font("helvetica", "I", 10)
        self.multi_cell(
            0,
            5,
            "CONFIDENTIAL\nThis document contains sensitive security information. Access is restricted to authorized personnel only.",
            align="C",
        )

    def management_summary(self, vulnerabilities):
        self.add_page()
        self.set_font("helvetica", "B", 20)
        self.cell(0, 15, "1. Management Summary", ln=True)
        self.ln(5)

        self.set_font("helvetica", "", 11)
        self.multi_cell(
            0,
            6,
            "This report provides an overview of the security posture of the assessed environment. The automated scan identified the following security findings which are categorized by their severity levels.",
        )
        self.ln(10)

        # Severity Counter
        stats = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for v in vulnerabilities:
            sev = v.get("severity", "INFO").upper()
            if sev in stats:
                stats[sev] += 1
            else:
                stats["INFO"] += 1

        # Draw small stats table
        self.set_font("helvetica", "B", 12)
        self.cell(60, 10, "Severity Level", border=1, align="C")
        self.cell(60, 10, "Count", border=1, align="C")
        self.ln()

        colors = {
            "CRITICAL": (150, 0, 0),
            "HIGH": (255, 0, 0),
            "MEDIUM": (255, 165, 0),
            "LOW": (0, 128, 0),
            "INFO": (0, 0, 255),
        }

        self.set_font("helvetica", "", 11)
        for label, count in stats.items():
            self.set_text_color(*colors[label])
            self.cell(60, 10, label, border=1, align="C")
            self.set_text_color(0)
            self.cell(60, 10, str(count), border=1, align="C")
            self.ln()

        self.ln(10)
        total = len(vulnerabilities)
        if total == 0:
            self.set_font("helvetica", "B", 12)
            self.set_text_color(0, 128, 0)
            self.cell(0, 10, "SUCCESS: No vulnerabilities detected.", ln=True)
        else:
            self.set_font("helvetica", "B", 12)
            self.set_text_color(150, 0, 0)
            self.cell(
                0,
                10,
                f"WARNING: {total} security findings require your attention.",
                ln=True,
            )
        self.set_text_color(0)

    def vulnerability_details(self, vulnerabilities):
        self.add_page()
        self.set_font("helvetica", "B", 20)
        self.cell(0, 15, "2. Detailed Findings", ln=True)
        self.ln(5)

        colors = {
            "CRITICAL": (150, 0, 0),
            "HIGH": (255, 0, 0),
            "MEDIUM": (255, 165, 0),
            "LOW": (0, 128, 0),
            "INFO": (0, 0, 255),
        }

        for idx, v in enumerate(vulnerabilities, 1):
            if self.get_y() > 220:
                self.add_page()

            sev = v.get("severity", "INFO").upper()
            color = colors.get(sev, (0, 0, 0))

            # Header Box
            self.set_fill_color(*color)
            self.set_text_color(255, 255, 255)
            self.set_font("helvetica", "B", 12)
            self.cell(
                0,
                10,
                f"Finding #{idx}: {v.get('vuln_type', 'Unknown')}",
                ln=True,
                fill=True,
            )

            # Metadata
            self.set_text_color(0)
            self.set_font("helvetica", "B", 10)
            self.cell(40, 8, "Severity:", border="B")
            self.set_font("helvetica", "", 10)
            self.set_text_color(*color)
            self.cell(0, 8, sev, border="B", ln=True)

            self.set_text_color(0)
            self.set_font("helvetica", "B", 10)
            self.cell(40, 8, "Target Endpoint:", border="B")
            self.set_font("helvetica", "", 10)
            self.cell(0, 8, v.get("target_endpoint", "N/A"), border="B", ln=True)

            # Description
            self.ln(2)
            self.set_font("helvetica", "B", 10)
            self.cell(0, 8, "Description:", ln=True)
            self.set_font("helvetica", "", 10)
            self.multi_cell(0, 6, v.get("description", "No description provided."))

            # Evidences
            evidences = v.get("evidences", [])
            if evidences:
                self.ln(2)
                self.set_font("helvetica", "B", 10)
                self.cell(0, 8, "Technical Evidence:", ln=True)
                for ev in evidences:
                    self.set_font("helvetica", "I", 9)
                    self.multi_cell(0, 5, f"Payload: {ev.get('payload_used', 'N/A')}")
                    loot = ev.get("loot_data")
                    if loot:
                        self.set_fill_color(240, 240, 240)
                        self.set_font("courier", "", 8)
                        self.multi_cell(0, 4, str(loot), border=1, fill=True)
                        self.ln(2)

            self.ln(10)


def build_report(scan_id, vulnerabilities):
    pdf = AegisReport(scan_id)
    pdf.set_title("Aegis AI Security Report")
    pdf.set_author("Aegis AI Automated Scanner")

    pdf.cover_page()
    pdf.management_summary(vulnerabilities)
    pdf.vulnerability_details(vulnerabilities)

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
