import AppKit
let directory = URL(fileURLWithPath: CommandLine.arguments[1])
try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
for size in [16,32,128,256,512] {
    for scale in [1,2] {
        let pixels = size * scale
        let image = NSImage(size: NSSize(width: pixels, height: pixels))
        image.lockFocus()
        let rect = NSRect(x: 0, y: 0, width: pixels, height: pixels)
        let inset = CGFloat(pixels) * 0.06
        let shape = NSBezierPath(roundedRect: rect.insetBy(dx: inset, dy: inset),
                                 xRadius: CGFloat(pixels)*0.20, yRadius: CGFloat(pixels)*0.20)
        NSGradient(starting: NSColor(red: 0.08, green: 0.25, blue: 0.44, alpha: 1),
                   ending: NSColor(red: 0.03, green: 0.07, blue: 0.15, alpha: 1))!.draw(in: shape, angle: -90)
        let label = CommandLine.arguments.count > 2 ? CommandLine.arguments[2] : "S"
        let text = label as NSString
        let attrs: [NSAttributedString.Key: Any] = [.font: NSFont.boldSystemFont(ofSize: CGFloat(pixels)*(label.count > 1 ? 0.32 : 0.60)), .foregroundColor: NSColor.white]
        let ts = text.size(withAttributes: attrs)
        text.draw(at: NSPoint(x: (CGFloat(pixels)-ts.width)/2, y: (CGFloat(pixels)-ts.height)/2),withAttributes: attrs)
        image.unlockFocus()
        let rep = NSBitmapImageRep(data: image.tiffRepresentation!)!
        let name = "icon_\(size)x\(size)" + (scale == 2 ? "@2x" : "") + ".png"
        try rep.representation(using: .png, properties: [:])!.write(to: directory.appendingPathComponent(name))
    }
}
