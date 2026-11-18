import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pdf_parser import PDFParserService
from app.services.rag import SleepGuideRetriever


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evalúa aceptación y rechazo del recuperador con el golden dataset."
    )
    parser.add_argument("--dataset", default="data/golden_dataset.csv")
    parser.add_argument("--pdf", default="app/data/documento_sueno.pdf")
    parser.add_argument(
        "--threshold",
        type=float,
        default=float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.10")),
        help="Umbral de similitud coseno entre 0 y 1 (por defecto: 0.10).",
    )
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        parser.error("--threshold debe estar entre 0 y 1")

    retriever = SleepGuideRetriever(PDFParserService(args.pdf).extract_pages())
    matrix = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    cases = []
    with open(args.dataset, newline="", encoding="utf-8") as dataset_file:
        for row in csv.DictReader(dataset_file):
            chunks = retriever.retrieve(row["pregunta"])
            similarity = chunks[0].similarity if chunks else 0.0
            predicted_answer = similarity >= args.threshold * 100
            expected_answer = row["comportamiento_esperado"] == "responder"
            if expected_answer and predicted_answer:
                matrix["tp"] += 1
            elif expected_answer:
                matrix["fn"] += 1
            elif predicted_answer:
                matrix["fp"] += 1
            else:
                matrix["tn"] += 1
            cases.append({
                "id": row["id"],
                "esperado": row["comportamiento_esperado"],
                "predicho": "responder" if predicted_answer else "rechazar",
                "similitud_porcentaje": similarity,
                "correcto": expected_answer == predicted_answer,
            })

    total = sum(matrix.values())
    result = {
        "umbral_porcentaje": round(args.threshold * 100, 2),
        "casos": total,
        "matriz_confusion": matrix,
        "precision_respuesta": round(
            matrix["tp"] / (matrix["tp"] + matrix["fp"]), 4
        ) if matrix["tp"] + matrix["fp"] else 0,
        "recall_respuesta": round(
            matrix["tp"] / (matrix["tp"] + matrix["fn"]), 4
        ) if matrix["tp"] + matrix["fn"] else 0,
        "tasa_rechazo_incorrecto": round(
            matrix["fp"] / (matrix["fp"] + matrix["tn"]), 4
        ) if matrix["fp"] + matrix["tn"] else 0,
        "exactitud_clasificacion": round(
            (matrix["tp"] + matrix["tn"]) / total, 4
        ) if total else 0,
        "detalle": cases,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(case["correcto"] for case in cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
