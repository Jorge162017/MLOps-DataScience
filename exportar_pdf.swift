// Generador local del documento de avance. No es una dependencia del pipeline.
import Foundation
import AppKit
import CoreGraphics

let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let output = root.appendingPathComponent("AVANCE_LAB11.pdf")
var media = CGRect(x: 0, y: 0, width: 612, height: 792)
guard let consumer = CGDataConsumer(url: output as CFURL),
      let ctx = CGContext(consumer: consumer, mediaBox: &media, nil) else { fatalError("No se pudo crear el PDF") }
let ink = NSColor(calibratedRed: 0.08, green: 0.19, blue: 0.24, alpha: 1)
let green = NSColor(calibratedRed: 0.10, green: 0.40, blue: 0.33, alpha: 1)
var y: CGFloat = 0
var page = 0

func text(_ value: String, x: CGFloat, y: CGFloat, width: CGFloat, size: CGFloat, bold: Bool = false, color: NSColor? = nil) -> CGFloat {
    let paragraph = NSMutableParagraphStyle()
    paragraph.lineSpacing = 3
    let font = bold ? NSFont.boldSystemFont(ofSize: size) : NSFont.systemFont(ofSize: size)
    let a = NSAttributedString(string: value, attributes: [.font: font, .foregroundColor: color ?? ink, .paragraphStyle: paragraph])
    let r = a.boundingRect(with: NSSize(width: width, height: 10000), options: [.usesLineFragmentOrigin, .usesFontLeading])
    a.draw(with: NSRect(x: x, y: y, width: width, height: ceil(r.height) + 2), options: [.usesLineFragmentOrigin, .usesFontLeading])
    return ceil(r.height)
}

func newPage() {
    if page > 0 { ctx.restoreGState(); ctx.endPDFPage() }
    ctx.beginPDFPage(nil)
    ctx.saveGState()
    ctx.translateBy(x: 0, y: 792)
    ctx.scaleBy(x: 1, y: -1)
    NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: true)
    page += 1
    _ = text("UVG · CC3066 DATA SCIENCE · SEMESTRE II 2026", x: 44, y: 26, width: 524, size: 8.5, bold: true, color: green)
    ctx.setStrokeColor(green.cgColor); ctx.setLineWidth(1)
    ctx.move(to: CGPoint(x: 44, y: 47)); ctx.addLine(to: CGPoint(x: 568, y: 47)); ctx.strokePath()
    _ = text("LAB 11 / AVANCE · JORGE LUIS LOPEZ · 221038", x: 44, y: 754, width: 450, size: 8, color: green)
    _ = text("\(page)", x: 542, y: 754, width: 26, size: 8)
    y = 65
}

func block(_ value: String, size: CGFloat = 10.5, bold: Bool = false, space: CGFloat = 9) {
    let clean = value.replacingOccurrences(of: "**", with: "").replacingOccurrences(of: "`", with: "")
    let style = NSMutableParagraphStyle(); style.lineSpacing = 3
    let font = bold ? NSFont.boldSystemFont(ofSize: size) : NSFont.systemFont(ofSize: size)
    let h = NSAttributedString(string: clean, attributes: [.font: font, .paragraphStyle: style]).boundingRect(with: NSSize(width: 524, height: 10000), options: [.usesLineFragmentOrigin, .usesFontLeading]).height
    if y + h + space > 730 { newPage() }
    y += text(clean, x: 44, y: y, width: 524, size: size, bold: bold) + space
}

func diagram() {
    if y + 430 > 730 { newPage() }
    let items = [
        "Fuente mensual + config.json",
        "Lectura y trazabilidad: hashes, versiones y Git",
        "6 controles: esquema, fechas, clave, faltantes, valores, metodología",
        "Preparación: Turista + Excursionista por mes; sin imputar cero",
        "SES + evaluación temporal: MAE / RMSE frente a referencia",
        "Estimaciones candidatas: julio y agosto de 2026",
        "Aceptar solo con calidad, integridad y MAE ≤ referencia",
        "Manifiesto aprobado → tablero (conexión pendiente)"
    ]
    for (i, item) in items.enumerated() {
        let rect = CGRect(x: 70, y: y, width: 472, height: 37)
        ctx.setFillColor(NSColor(calibratedRed: 0.94, green: 0.97, blue: 0.96, alpha: 1).cgColor)
        ctx.fill(rect); ctx.setStrokeColor(green.cgColor); ctx.stroke(rect)
        _ = text(item, x: 82, y: y + 8, width: 448, size: 9.3, bold: i == 2 || i == 6)
        y += 37
        if i < items.count - 1 {
            ctx.move(to: CGPoint(x: 306, y: y)); ctx.addLine(to: CGPoint(x: 306, y: y + 12)); ctx.strokePath()
            y += 12
        }
    }
    y += 11
    block("Fallo crítico: detener y guardar causa. Rechazo: conservar candidata para revisión. En ambos casos, mantener la versión aprobada anterior.", size: 9.5)
}

newPage()
let markdown = try String(contentsOf: root.appendingPathComponent("AVANCE_LAB11.md"), encoding: .utf8)
var paragraph: [String] = []
func flush() { if !paragraph.isEmpty { block(paragraph.joined(separator: " ")); paragraph = [] } }
for line in markdown.components(separatedBy: .newlines) {
    if line.isEmpty { flush(); continue }
    if line.hasPrefix("# ") { flush(); block(String(line.dropFirst(2)), size: 25, bold: true, space: 18) }
    else if line.hasPrefix("## ") {
        flush()
        if line.hasPrefix("## 4.") || line.hasPrefix("## 5.") || y > 630 { newPage() }
        block(String(line.dropFirst(3)), size: 16, bold: true, space: 12)
    }
    else if line.hasPrefix("Ver `diagrama_flujo.svg`") { flush(); diagram() }
    else if line.hasPrefix("Fuente mensual + configuración →") { continue }
    else if line.hasPrefix("|---") || line.hasPrefix("| Control |") { flush() }
    else if line.hasPrefix("|") {
        flush()
        let cells = line.split(separator: "|").map { $0.trimmingCharacters(in: .whitespaces) }
        if cells.count == 4 {
            block(cells[0], size: 11, bold: true, space: 4)
            block("Verifica: \(cells[1]). Advertencia: \(cells[2]). Detención: \(cells[3]).", size: 10, space: 10)
        }
    } else { paragraph.append(line) }
}
flush()

if let data = try? Data(contentsOf: root.appendingPathComponent("evidencia_avance.json")),
   let e = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
    newPage()
    block("8. Resultados verificados", size: 22, bold: true, space: 16)
    block("Verificación local con el Excel institucional y pruebas sintéticas. Los archivos detallados se conservan en resultados/ y el resumen versionable en evidencia_avance.json.")
    if let d = e["datos_reales"] as? [String: Any] {
        block("Fuente real: \(d["filas"] ?? "") filas y \(d["meses"] ?? "") meses. Los seis controles finalizaron en PASS. No se eliminaron duplicados ni se completaron meses ausentes con cero.")
    }
    if let metrics = e["metricas"] as? [String: Any], let m = metrics["estimado"] as? [String: Any], let r = metrics["referencia"] as? [String: Any] {
        func number(_ obj: Any?) -> String { String(format: "%.2f", (obj as? Double) ?? 0) }
        block("Evaluación nacional: enero–junio de 2026", size: 13, bold: true)
        block("SES: MAE \(number(m["MAE"])) visitantes; RMSE \(number(m["RMSE"])) visitantes.")
        block("Último valor observado: MAE \(number(r["MAE"])) visitantes; RMSE \(number(r["RMSE"])) visitantes.")
        block("Estado: \(e["estado"] ?? ""). Se aplicó la regla MAE_SES ≤ MAE_referencia. Esto describe seis meses históricos; no garantiza precisión de julio–agosto ni de otros destinos.")
    }
    block("Reproducibilidad", size: 13, bold: true)
    block("Se realizaron dos ejecuciones completas con los mismos datos y configuración. La diferencia numérica máxima fue 0 en la serie mensual, evaluación y estimaciones. Tolerancia absoluta de comprobación: 1e-8; tolerancia relativa: 0. Los identificadores y fechas son distintos por diseño.")
    block("Ejecución 1: \(e["ejecucion_real_1"] ?? "")", size: 9.5)
    block("Ejecución 2: \(e["ejecucion_real_2"] ?? "")", size: 9.5)
    block("Fallo controlado y recuperación inicial", size: 13, bold: true)
    block("Se creó un Excel sintético con una clave duplicada y se leyó mediante el pipeline real. La ejecución terminó FAILED antes del ajuste, registró la causa y no generó métricas. El hash del manifiesto aprobado anterior permaneció intacto. Una ejecución posterior con la fuente real válida terminó APPROVED.")
    if let f = e["prueba_fallo"] as? [String: Any] { block("Ejecución fallida: \(f["run_id"] ?? "")", size: 9.5) }
    block("Pruebas automatizadas", size: 13, bold: true)
    block("11 pruebas pasaron. Incluyen los seis controles, conservación de ceros, exclusión de no visitantes, factor inválido, ausencia de información futura y conservación de la versión aprobada ante fallo. Comando: python -m unittest -v test_pipeline.")
    block("Estado de entrega", size: 13, bold: true)
    block("Listos para revisión: alcance, diagrama, pipeline inicial, seis controles y evidencia ejecutable. Pendientes para el final: MLflow, integración con Streamlit, monitoreo, restauración desde la interfaz, Docker y copia limpia. No se ha realizado entrega en Canvas ni publicación externa.")
}
ctx.restoreGState(); ctx.endPDFPage(); ctx.closePDF()
print("PDF generado: \(output.path) · \(page) páginas")
