"""
data/create_sample_pdfs.py
──────────────────────────────────────────────────────────────────────────────
Generates realistic sample legal contract PDFs for demo purposes using fpdf2.
Creates two documents:
  - sample_nda.pdf        -- Non-Disclosure Agreement (8 pages)
  - sample_employment.pdf -- Employment Contract (10 pages)
"""
from fpdf import FPDF
from pathlib import Path

OUT = Path(__file__).parent


class LegalPDF(FPDF):
    def __init__(self, title: str):
        super().__init__()
        self.doc_title = title
        self.set_auto_page_break(auto=True, margin=25)
        self.add_page()

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, self.doc_title, align="R")
        self.ln(4)
        self.set_draw_color(200, 200, 200)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def h1(self, text: str):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(20, 40, 80)
        self.ln(4)
        self.cell(0, 10, text)
        self.ln(8)
        self.set_text_color(0, 0, 0)

    def h2(self, text: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(30, 60, 110)
        self.ln(3)
        self.cell(0, 8, text)
        self.ln(5)
        self.set_text_color(0, 0, 0)

    def body(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, text)
        self.ln(3)


NDA_SECTIONS = [
    ("NON-DISCLOSURE AGREEMENT", None),
    (None, (
        "This Non-Disclosure Agreement (\"Agreement\") is entered into as of January 15, 2024 "
        "(\"Effective Date\"), by and between Apex Technologies Inc., a Delaware corporation "
        "with its principal place of business at 100 Innovation Drive, San Francisco, CA 94105 "
        "(\"Disclosing Party\"), and Orion Analytics LLC, a limited liability company organized "
        "under the laws of New York, with its principal place of business at 200 Data Boulevard, "
        "New York, NY 10001 (\"Receiving Party\"). Each party is referred to individually as a "
        "\"Party\" and collectively as the \"Parties\"."
    )),
    ("1. PURPOSE", None),
    (None, (
        "The Parties wish to explore a potential business relationship related to the development "
        "of artificial intelligence-based analytics solutions (the \"Purpose\"). In connection with "
        "this Purpose, each Party may disclose to the other certain confidential and proprietary "
        "information. The Parties desire to protect such information from unauthorized use or "
        "disclosure in accordance with the terms set forth herein."
    )),
    ("2. DEFINITION OF CONFIDENTIAL INFORMATION", None),
    (None, (
        "\"Confidential Information\" means any and all non-public information, in any form or "
        "medium (written, oral, electronic, or otherwise), disclosed by the Disclosing Party to "
        "the Receiving Party in connection with the Purpose, including without limitation: "
        "(a) trade secrets, inventions, and know-how; (b) financial information, projections, "
        "and business plans; (c) customer lists, supplier information, and marketing strategies; "
        "(d) technical data, algorithms, source code, and software; and (e) any other information "
        "that a reasonable person would consider confidential under the circumstances. "
        "Confidential Information does not include information that: (i) is or becomes publicly "
        "available through no fault of the Receiving Party; (ii) was already known to the Receiving "
        "Party prior to disclosure; (iii) is independently developed by the Receiving Party without "
        "use of the Disclosing Party's Confidential Information; or (iv) is required to be disclosed "
        "by applicable law or court order, provided the Receiving Party gives prompt written notice "
        "to the Disclosing Party and cooperates in seeking a protective order."
    )),
    ("3. OBLIGATIONS OF RECEIVING PARTY", None),
    (None, (
        "The Receiving Party agrees to: (a) hold all Confidential Information in strict confidence "
        "using at least the same degree of care it uses to protect its own confidential information, "
        "but no less than reasonable care; (b) not disclose any Confidential Information to any "
        "third party without the prior written consent of the Disclosing Party; (c) use the "
        "Confidential Information solely for the Purpose; (d) limit access to the Confidential "
        "Information to its employees, officers, directors, attorneys, accountants, and financial "
        "advisors (collectively, \"Representatives\") who have a need to know such information for "
        "the Purpose and who are bound by confidentiality obligations at least as restrictive as "
        "those contained herein; (e) promptly notify the Disclosing Party upon becoming aware of "
        "any unauthorized use or disclosure of Confidential Information."
    )),
    ("4. TERM AND TERMINATION", None),
    (None, (
        "This Agreement shall commence on the Effective Date and shall continue for a period of "
        "three (3) years, unless earlier terminated by either Party upon thirty (30) days' written "
        "notice to the other Party. The obligations of confidentiality set forth herein shall "
        "survive termination or expiration of this Agreement for an additional period of five (5) "
        "years. Upon termination, or upon the written request of the Disclosing Party, the "
        "Receiving Party shall promptly destroy or return all materials containing Confidential "
        "Information and certify in writing that it has done so."
    )),
    ("5. INTELLECTUAL PROPERTY", None),
    (None, (
        "Nothing in this Agreement shall be construed to grant the Receiving Party any license, "
        "right, title, or interest in or to the Confidential Information or any intellectual "
        "property rights of the Disclosing Party. All Confidential Information remains the sole "
        "and exclusive property of the Disclosing Party. Any inventions, improvements, or "
        "derivative works created by the Receiving Party based on or derived from the Confidential "
        "Information shall be considered work-for-hire owned exclusively by the Disclosing Party, "
        "or if not so considered, shall be irrevocably assigned to the Disclosing Party."
    )),
    ("6. INDEMNIFICATION", None),
    (None, (
        "The Receiving Party shall indemnify, defend, and hold harmless the Disclosing Party and "
        "its officers, directors, employees, agents, successors, and assigns (collectively, "
        "\"Indemnified Parties\") from and against any and all claims, actions, suits, proceedings, "
        "losses, damages, liabilities, costs, and expenses (including reasonable attorneys' fees) "
        "arising out of or relating to: (a) any breach of this Agreement by the Receiving Party "
        "or its Representatives; (b) any unauthorized use or disclosure of Confidential Information "
        "by the Receiving Party or its Representatives; or (c) the gross negligence or willful "
        "misconduct of the Receiving Party. The Disclosing Party shall promptly notify the "
        "Receiving Party of any claim for which indemnification is sought and shall cooperate "
        "reasonably in the defense of such claim."
    )),
    ("7. LIMITATION OF LIABILITY", None),
    (None, (
        "IN NO EVENT SHALL EITHER PARTY BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, "
        "SPECIAL, CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES, INCLUDING LOST PROFITS, LOSS "
        "OF DATA, OR LOSS OF GOODWILL, ARISING OUT OF OR RELATED TO THIS AGREEMENT, EVEN IF "
        "SUCH PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES. THE TOTAL CUMULATIVE "
        "LIABILITY OF EITHER PARTY ARISING OUT OF OR RELATED TO THIS AGREEMENT SHALL NOT EXCEED "
        "THE GREATER OF: (A) THE TOTAL FEES PAID BY THE RECEIVING PARTY TO THE DISCLOSING PARTY "
        "UNDER THIS AGREEMENT IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM; OR (B) ONE THOUSAND "
        "DOLLARS ($1,000)."
    )),
    ("8. GOVERNING LAW AND DISPUTE RESOLUTION", None),
    (None, (
        "This Agreement shall be governed by and construed in accordance with the laws of the "
        "State of Delaware, without regard to its conflict of laws principles. Any dispute, "
        "controversy, or claim arising out of or relating to this Agreement, or the breach, "
        "termination, or invalidity thereof, shall first be submitted to non-binding mediation "
        "in San Francisco, California. If mediation fails within sixty (60) days, the dispute "
        "shall be resolved by binding arbitration under the rules of the American Arbitration "
        "Association. The parties consent to the exclusive jurisdiction of the state and federal "
        "courts located in Delaware for enforcement of any arbitration award."
    )),
    ("9. GENERAL PROVISIONS", None),
    (None, (
        "9.1 Entire Agreement. This Agreement constitutes the entire agreement between the Parties "
        "with respect to its subject matter and supersedes all prior agreements, representations, "
        "and understandings. 9.2 Amendments. This Agreement may not be amended except by a written "
        "instrument signed by authorized representatives of both Parties. 9.3 Waiver. No waiver of "
        "any provision of this Agreement shall be effective unless in writing. 9.4 Severability. "
        "If any provision is held invalid or unenforceable, the remaining provisions shall remain "
        "in full force and effect. 9.5 Counterparts. This Agreement may be executed in counterparts, "
        "each of which shall be deemed an original. 9.6 Electronic Signatures. Electronic signatures "
        "shall be deemed valid and binding to the same extent as original signatures."
    )),
    ("10. SIGNATURES", None),
    (None, (
        "IN WITNESS WHEREOF, the Parties have executed this Non-Disclosure Agreement as of the "
        "Effective Date written above.\n\n"
        "APEX TECHNOLOGIES INC.\n"
        "By: ______________________________\n"
        "Name: Sarah J. Mitchell\n"
        "Title: Chief Executive Officer\n"
        "Date: January 15, 2024\n\n"
        "ORION ANALYTICS LLC\n"
        "By: ______________________________\n"
        "Name: David R. Chen\n"
        "Title: Managing Partner\n"
        "Date: January 15, 2024"
    )),
]


def create_nda():
    pdf = LegalPDF("Non-Disclosure Agreement - Apex Technologies / Orion Analytics")
    for heading, body in NDA_SECTIONS:
        if heading:
            if heading == "NON-DISCLOSURE AGREEMENT":
                pdf.h1(heading)
            else:
                pdf.h2(heading)
        if body:
            pdf.body(body)
    path = OUT / "sample_nda.pdf"
    pdf.output(str(path))
    print(f"[OK] Created {path}")


EMPLOYMENT_SECTIONS = [
    ("EMPLOYMENT AGREEMENT", None),
    (None, (
        "This Employment Agreement (\"Agreement\") is entered into as of March 1, 2024 "
        "(\"Effective Date\"), between Nexus Biotech Corporation, a California corporation "
        "(\"Company\"), and Dr. Elena Vasquez (\"Employee\"). The Company desires to employ "
        "Employee on the terms set forth herein, and Employee desires to accept such employment."
    )),
    ("1. POSITION AND DUTIES", None),
    (None, (
        "The Company hereby employs Employee as Vice President of Research and Development. "
        "Employee shall report to the Chief Scientific Officer and shall perform such duties "
        "as are consistent with this position, including leading all R&D initiatives, managing "
        "a team of 25 scientists and engineers, overseeing clinical trial design, and representing "
        "the Company at industry conferences. Employee agrees to devote their full professional "
        "time, attention, and energies to the performance of their duties and shall not engage "
        "in any other business activity, paid or unpaid, without prior written consent of the "
        "Company's Board of Directors."
    )),
    ("2. COMPENSATION", None),
    (None, (
        "2.1 Base Salary. The Company shall pay Employee an annual base salary of $285,000 "
        "(Two Hundred Eighty-Five Thousand Dollars), payable in accordance with the Company's "
        "standard payroll schedule, less applicable withholdings and deductions. "
        "2.2 Performance Bonus. Employee shall be eligible for an annual performance bonus "
        "of up to 30% of base salary, based on achievement of mutually agreed-upon milestones. "
        "2.3 Equity. Employee shall receive stock options to purchase 150,000 shares of Company "
        "common stock at an exercise price equal to the fair market value on the grant date, "
        "subject to a four-year vesting schedule with a one-year cliff. "
        "2.4 Benefits. Employee shall be entitled to participate in all benefit plans offered "
        "to similarly situated employees, including medical, dental, vision, 401(k) with 4% "
        "employer match, and unlimited paid time off."
    )),
    ("3. TERM OF EMPLOYMENT", None),
    (None, (
        "Employment under this Agreement shall commence on the Effective Date and continue "
        "until terminated in accordance with Section 6. This is an at-will employment "
        "relationship, meaning that either Party may terminate this Agreement at any time, "
        "with or without cause, subject to the notice requirements and severance provisions "
        "set forth herein."
    )),
    ("4. INTELLECTUAL PROPERTY ASSIGNMENT", None),
    (None, (
        "Employee agrees to promptly disclose and assign to the Company all inventions, "
        "discoveries, improvements, and innovations (collectively, \"Inventions\") conceived, "
        "reduced to practice, or developed by Employee, either alone or jointly with others, "
        "during the term of employment that: (a) relate to the Company's current or reasonably "
        "anticipated business or research activities; (b) result from work performed by Employee "
        "for the Company; or (c) are developed using the Company's equipment, supplies, or "
        "facilities. Employee hereby irrevocably assigns all right, title, and interest in such "
        "Inventions to the Company, including all patent, copyright, trade secret, and other "
        "intellectual property rights therein."
    )),
    ("5. NON-COMPETE AND NON-SOLICITATION", None),
    (None, (
        "5.1 Non-Compete. During employment and for a period of twelve (12) months following "
        "termination, Employee shall not, directly or indirectly, engage in or have any interest "
        "in any entity that competes with the Company in the field of oncology drug discovery "
        "within the United States. "
        "5.2 Non-Solicitation of Employees. During employment and for twenty-four (24) months "
        "following termination, Employee shall not solicit, recruit, or induce any Company "
        "employee to leave their employment with the Company. "
        "5.3 Non-Solicitation of Customers. During the same period, Employee shall not solicit "
        "any customer, client, or partner of the Company with whom Employee had material contact "
        "during the last two years of employment."
    )),
    ("6. TERMINATION AND SEVERANCE", None),
    (None, (
        "6.1 Termination Without Cause. If the Company terminates Employee's employment without "
        "Cause (as defined below), the Company shall provide: (a) twelve (12) months of base "
        "salary continuation; (b) continuation of health benefits for twelve (12) months; "
        "and (c) acceleration of vesting for 25% of unvested equity awards. "
        "6.2 Termination for Cause. If the Company terminates Employee's employment for Cause, "
        "Employee shall be entitled to receive only accrued and unpaid salary through the "
        "termination date. \"Cause\" means: (i) material breach of this Agreement; (ii) fraud, "
        "misappropriation, or dishonesty; (iii) conviction of a felony; or (iv) willful misconduct "
        "materially harmful to the Company. "
        "6.3 Resignation. Employee may resign upon sixty (60) days' written notice. The Company "
        "may elect to waive the notice period and provide payment in lieu of notice."
    )),
    ("7. GOVERNING LAW", None),
    (None, (
        "This Agreement shall be governed by and construed in accordance with the laws of the "
        "State of California. Any disputes arising under this Agreement shall be resolved by "
        "binding arbitration in San Francisco, California, under the JAMS Employment Arbitration "
        "Rules. Notwithstanding the foregoing, either Party may seek injunctive relief in any "
        "court of competent jurisdiction for actual or threatened breach of Sections 4 or 5."
    )),
    ("8. ENTIRE AGREEMENT", None),
    (None, (
        "This Agreement constitutes the entire understanding between the Parties concerning "
        "its subject matter and supersedes all prior negotiations, representations, warranties, "
        "and understandings. This Agreement may not be modified except by a written instrument "
        "signed by both Parties. If any provision is found invalid, the remaining provisions "
        "shall continue in full force and effect."
    )),
]


def create_employment():
    pdf = LegalPDF("Employment Agreement - Nexus Biotech Corporation / Dr. Elena Vasquez")
    for heading, body in EMPLOYMENT_SECTIONS:
        if heading:
            if heading == "EMPLOYMENT AGREEMENT":
                pdf.h1(heading)
            else:
                pdf.h2(heading)
        if body:
            pdf.body(body)
    path = OUT / "sample_employment.pdf"
    pdf.output(str(path))
    print(f"[OK] Created {path}")


if __name__ == "__main__":
    create_nda()
    create_employment()
    print("\nSample PDFs ready in data/")
    print("  - sample_nda.pdf        -- Non-Disclosure Agreement")
    print("  - sample_employment.pdf -- Employment Contract")
