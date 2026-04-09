#!/usr/bin/env python3
"""
scripts/ingest_papers.py
Scans the data/past_papers folder, finds PDFs, extracts text using the
OCR pipeline, and saves a .txt copy alongside each PDF.
Run this ONCE after adding new PDFs to pre-build the text cache.

Usage:
  python scripts/ingest_papers.py
  python scripts/ingest_papers.py --force   (re-extract even if .txt exists)

Also provides --demo  to create sample text files for testing.
"""

import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

BASE_DATA = Path(__file__).parent.parent / "data" / "past_papers"


def ingest_all(force: bool = False):
    """Walk all folders and extract text from PDFs."""
    pdfs = list(BASE_DATA.rglob("*.pdf"))
    if not pdfs:
        print("No PDF files found under data/past_papers/")
        return

    print(f"Found {len(pdfs)} PDF(s). Extracting text…\n")

    from utils.ocr_pipeline import extract_text_from_pdf

    for pdf in pdfs:
        txt_path = pdf.with_suffix(".txt")
        if txt_path.exists() and not force:
            print(f"  SKIP (already extracted): {pdf.name}")
            continue
        try:
            text = extract_text_from_pdf(pdf)
            txt_path.write_text(text, encoding="utf-8")
            print(f"  OK  {pdf.name}  →  {txt_path.name}  ({len(text)} chars)")
        except Exception as e:
            print(f"  ERR {pdf.name}: {e}")

    print("\nDone.")


def create_demo_papers():
    """
    Create sample .txt past papers to test the system WITHOUT real PDFs.
    Covers Grade12 / Federal Board / Physics  (2021–2023).
    """
    samples = {
        "Grade12/Federal Board/Physics/2021.txt": """
FEDERAL BOARD OF INTERMEDIATE AND SECONDARY EDUCATION
ISLAMABAD
Annual Examination 2021
Subject: Physics (XII)   Time: 3 Hours   Max Marks: 85

SECTION A — MCQs (Objective Type)
Q1. The SI unit of electric potential is:
(a) Coulomb  (b) Volt  (c) Ampere  (d) Ohm

Q2. Which law states that the force between two charges is proportional to the product of charges?
(a) Ohm's Law  (b) Coulomb's Law  (c) Faraday's Law  (d) Newton's Law

Q3. The phenomenon of electromagnetic induction was discovered by:
(a) Newton  (b) Coulomb  (c) Faraday  (d) Maxwell

SECTION B — Short Questions (2 marks each)
Q4. Define electric field intensity. Give its SI unit.
Q5. State Ohm's law and write its mathematical form.
Q6. What is meant by simple harmonic motion? Give two examples.
Q7. Define critical angle and total internal reflection.
Q8. State Newton's second law of motion. Write its equation.
Q9. What is meant by wave velocity? How is it related to frequency and wavelength?
Q10. Define specific heat capacity. Give its SI unit.

SECTION C — Long Questions (5 marks each, attempt any 5)
Q11. (a) Explain Coulomb's law of electrostatics. Derive the expression for electric force between two charges.
     (b) What is meant by electric field lines? State their properties.

Q12. (a) Derive the equation of motion under gravity. Explain projectile motion.
     (b) A ball is thrown horizontally with 20 m/s from a height of 45 m. Calculate the time of flight and range.

Q13. (a) Explain Faraday's law of electromagnetic induction. State Lenz's law.
     (b) What is an AC generator? Explain its working principle with a diagram.

Q14. (a) Explain simple harmonic motion. Derive the expression for the period of a simple pendulum.
     (b) What is resonance? Give two applications of resonance in daily life.

Q15. (a) Describe the photoelectric effect. State Einstein's photoelectric equation.
     (b) Define work function and threshold frequency. What is de Broglie hypothesis?
""",
        "Grade12/Federal Board/Physics/2022.txt": """
FEDERAL BOARD OF INTERMEDIATE AND SECONDARY EDUCATION
ISLAMABAD
Annual Examination 2022
Subject: Physics (XII)   Time: 3 Hours   Max Marks: 85

SECTION A — Objective Type
Q1. The unit of magnetic flux is:
(a) Tesla  (b) Weber  (c) Henry  (d) Farad

Q2. Which equation represents Coulomb's law?
(a) F = ma  (b) F = kq1q2/r²  (c) F = qvB  (d) F = BIl

Q3. Total internal reflection occurs when light passes from:
(a) Rarer to denser medium  (b) Denser to rarer medium at angle > critical angle  (c) Air to glass  (d) None

SECTION B — Short Questions
Q4. Define capacitance. Give its unit.
Q5. State Faraday's first and second law of electrolysis.
Q6. Define amplitude and frequency of a wave.
Q7. What is the difference between transverse and longitudinal waves?
Q8. State Newton's law of gravitation. Define gravitational constant G.
Q9. What is Doppler effect? Give two examples.
Q10. Define entropy. State the second law of thermodynamics.

SECTION C — Long Questions (attempt any 5)
Q11. (a) Derive the expression for the electric potential at a point due to a point charge.
     (b) Define equipotential surface. What is the work done in moving a charge along an equipotential surface?

Q12. (a) Explain the working of a transformer. Derive the turns ratio equation.
     (b) Define self-inductance and mutual inductance with units.

Q13. (a) Describe the refraction of light through a prism. Derive the expression for the angle of deviation.
     (b) What are optical fibres? Explain their working principle and applications.

Q14. (a) Explain Bohr's atomic model. Write postulates of Bohr's model.
     (b) Calculate the energy of an electron in the nth orbit of hydrogen atom.

Q15. (a) What is nuclear fission? Explain a chain reaction with a diagram.
     (b) Define half-life. The half-life of a radioactive substance is 20 years. Calculate the fraction remaining after 60 years.
""",
        "Grade12/Federal Board/Physics/2023.txt": """
FEDERAL BOARD OF INTERMEDIATE AND SECONDARY EDUCATION
ISLAMABAD
Annual Examination 2023
Subject: Physics (XII)   Time: 3 Hours   Max Marks: 85

SECTION A — MCQs
Q1. The dimension of Planck's constant is:
(a) [ML²T⁻¹]  (b) [MLT⁻²]  (c) [ML²T⁻²]  (d) [ML⁻¹T]

Q2. In Coulomb's law, if the distance between two charges is doubled, the force becomes:
(a) Double  (b) Half  (c) Four times  (d) One-fourth

Q3. Lenz's law is a consequence of the law of conservation of:
(a) Charge  (b) Momentum  (c) Energy  (d) Mass

SECTION B — Short Questions
Q4. Explain the concept of electric flux. Write Gauss's law.
Q5. Define resistance and resistivity. What factors affect resistance?
Q6. What is meant by alternating current? Define peak value and RMS value.
Q7. State laws of refraction (Snell's law). Write the mathematical form.
Q8. Define kinetic energy and potential energy. Give the law of conservation of energy.
Q9. What is meant by simple harmonic motion? State its characteristics.
Q10. Define radioactivity. Name three types of radiations emitted by radioactive nuclei.

SECTION C — Long Questions (attempt any 5)
Q11. (a) Derive the expression for electric field intensity due to an infinite line charge.
     (b) Define dielectric constant. Explain the effect of inserting a dielectric in a capacitor.

Q12. (a) Explain Coulomb's law in vector form. Compare it with Newton's law of gravitation.
     (b) What is meant by electric potential energy? Derive an expression for it.

Q13. (a) Describe the construction and working of a CRO (cathode ray oscilloscope).
     (b) Explain the working principle of a DC motor.

Q14. (a) Explain simple harmonic motion with reference to a spring-mass system.
     (b) Derive the expression for the velocity and acceleration of a particle executing SHM.

Q15. (a) Explain the nuclear reactor. Name its major components and their functions.
     (b) What is radioactive decay? Derive the radioactive decay law.
""",
        "Grade12/Sindh Board/Physics/2022.txt": """
SINDH BOARD OF INTERMEDIATE EDUCATION, KARACHI
Annual Examination 2022
Subject: Physics   Time: 3 Hours   Marks: 80

Part I — MCQs
1. The dimensional formula of power is:
(a) ML²T⁻³  (b) MLT⁻²  (c) ML²T⁻²  (d) MLT⁻¹

2. Newton's third law states:
(a) F = ma  (b) Every action has equal and opposite reaction  (c) F ∝ rate of change of momentum

Part II — Short Answers
Q1. Define torque and angular momentum. Write the relation between them.
Q2. State Hooke's law. Define spring constant.
Q3. What is Bernoulli's theorem? Give one application.
Q4. Define temperature and heat. What are the scales of temperature?
Q5. What is electromagnetic induction? State Faraday's laws.

Part III — Detailed Answers
Q1. Explain Newton's laws of motion with examples.
    (a) First law — inertia and its applications
    (b) Second law — F = ma derivation
    (c) Third law — examples in rockets and swimming

Q2. Describe the phenomenon of interference of light. Explain Young's double slit experiment.
    Derive the formula for fringe width.

Q3. Describe Bohr's model of hydrogen atom. Derive the expression for the radius of nth orbit.
    What are the limitations of Bohr's model?

Q4. Explain electromagnetic waves. List properties of electromagnetic spectrum.
    What is polarization of light?
""",
        "Grade12/Karachi Board/Chemistry/2022.txt": """
KARACHI BOARD OF INTERMEDIATE EDUCATION
Annual Examination 2022
Subject: Chemistry (XII)   Time: 3 Hours

SECTION A
Q1. The hybridization of carbon in methane (CH₄) is:
(a) sp  (b) sp²  (c) sp³  (d) sp³d

Q2. Which type of bond is formed between Na and Cl?
(a) Covalent  (b) Ionic  (c) Metallic  (d) Hydrogen bond

SECTION B
Q3. Define oxidation and reduction in terms of electron transfer.
Q4. State Le Chatelier's principle with two applications.
Q5. Define pH. Calculate the pH of 0.01 M HCl solution.
Q6. What is an ester? Write the reaction for the formation of ethyl acetate.
Q7. Define activation energy. How does a catalyst affect activation energy?
Q8. What are alkenes? Give the general formula and write the structure of ethene.

SECTION C
Q9. (a) Explain the electrochemical series. What are its applications?
    (b) Calculate the EMF of a cell: Zn | Zn²⁺ || Cu²⁺ | Cu

Q10. (a) Define carboxylic acids. Explain their physical and chemical properties.
     (b) What is saponification? Write the equation.

Q11. (a) Explain the principle of Le Chatelier with reference to Haber process.
     (b) Define Kc and Kp. Derive the relation between them.
""",
    }

    created = 0
    for rel_path, content in samples.items():
        full_path = BASE_DATA / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if not full_path.exists():
            full_path.write_text(content.strip(), encoding="utf-8")
            print(f"  Created: {rel_path}")
            created += 1
        else:
            print(f"  Exists:  {rel_path}")

    print(f"\n{created} demo file(s) created.")
    print("Now run:  python backend/app.py")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="StudyLens Paper Ingestion Tool")
    parser.add_argument("--force", action="store_true", help="Re-extract even if .txt exists")
    parser.add_argument("--demo",  action="store_true", help="Create sample papers for testing")
    args = parser.parse_args()

    if args.demo:
        create_demo_papers()
    else:
        ingest_all(force=args.force)


if __name__ == "__main__":
    main()
