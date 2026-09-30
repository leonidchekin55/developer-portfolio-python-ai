import AppKit
import AVFoundation
import CoreText
import CoreVideo
import Foundation

struct Scene {
    let eyebrow: String
    let title: String
    let description: String
    let flow: [String]
    let bullets: [String]
    let narration: String
}

let scenes = [
    Scene(eyebrow: "LEONID · PYTHON BACKEND + APPLIED AI", title: "Шесть проектов.\nОдна инженерная база.", description: "Короткий обзор портфолио AI Engineer", flow: ["Python", "FastAPI", "PostgreSQL", "Docker + CI"], bullets: ["Агенты · RAG · обработка документов · evals", "Публичное демо работает без платных API"], narration: "Привет! Я Леонид, Python backend разработчик. Это короткий обзор моего портфолио AI Engineer: шесть самостоятельных проектов на Python и FastAPI, объединённых общей инженерной основой."),
    Scene(eyebrow: "01 · AI-МЕНЕДЖЕР ЗАЯВОК", title: "От сообщения\nдо проверенного черновика", description: "Структурированный вывод и действие под контролем человека", flow: ["Запрос клиента", "Валидированный JSON", "Черновик CRM", "Подтверждение"], bullets: ["Tool calling не может обойти роль и проверку схемы", "CRM, email и Sheets в демо — только mock"], narration: "Первый сценарий разбирает заявку и приводит данные к проверяемой структуре. Агент готовит действие как черновик и просит человека его подтвердить. CRM, письма и таблицы представлены mock-коннекторами: реальная запись не выполняется."),
    Scene(eyebrow: "02 · KNOWLEDGE BASE", title: "Ответ с опорой\nна источник", description: "Chunking · гибридный поиск · цитаты · права владельца", flow: ["PDF / DOCX / TXT", "Фрагменты", "Lexical + vector", "Цитата"], bullets: ["Локальный FastEmbed — опционально и без API-вызовов", "Render Free остаётся в лёгком hash/mock режиме"], narration: "В базе знаний документы разбиваются на фрагменты, ищутся по тексту и векторам, а ответ возвращает цитату исходного места. Дополнительно локально можно включить мультиязычную FastEmbed модель и переиндексировать документы. Бесплатная публичная версия остаётся в облегчённом режиме."),
    Scene(eyebrow: "03 + 04 · PROCESSING & EVALS", title: "Обработка и качество\nможно наблюдать", description: "Очередь задач, статусы, версии prompt и диагностические метрики", flow: ["Batch upload", "Redis + Celery", "Status / retry", "Trace + eval"], bullets: ["Локальный набор из 8 paraphrase-вопросов сравнивает Recall@k", "Метрики учебные, не обещают качество на любой базе"], narration: "Document Processor показывает пакетную обработку, очередь Redis и Celery, статусы и повторную обработку. Evals сохраняют trace, версию prompt, latency и стоимость. Для retrieval есть отдельное сравнение текстового и локального dense-поиска на небольшом синтетическом наборе; его показатели только диагностические."),
    Scene(eyebrow: "06 · SECURE AI AGENT", title: "Чтение доступно.\nЗапись требует approval.", description: "Роли · allowlist инструментов · аудит · блокировка типовых атак", flow: ["User role", "Allowed tool", "Audit event", "Human approval"], bullets: ["В demo используются только синтетические CRM-записи", "Injection фильтр показательный, не абсолютная защита"], narration: "Secure Agent разделяет роли, ограничивает инструменты, пишет аудит и блокирует некоторые типовые prompt-injection запросы. Записывающее действие остаётся неподтверждённым черновиком. Защита показательная, а не абсолютная."),
    Scene(eyebrow: "05 · DEPLOYMENT & OBSERVABILITY", title: "Проверки доходят\nдо опубликованного сервиса", description: "GitHub Actions · online Docker build · Render · post-deploy smoke", flow: ["Tests", "Docker build", "Render live", "Smoke × 6"], bullets: ["Все проверки используют временные mock-сессии", "Free-сервис может засыпать и сбрасывать данные"], narration: "GitHub Actions запускает тесты и собирает Docker образ онлайн. После успешного CI workflow проверяет опубликованные страницы и все шесть безопасных сценариев, а затем удаляет свои демо-сессии. Бесплатный Render может засыпать, а временные данные могут сбрасываться."),
    Scene(eyebrow: "ПОПРОБУЙТЕ САМИ", title: "Откройте интерактивную\nпесочницу", description: "Синтетические данные · без токена · без платных моделей", flow: ["Все 6 сценариев", "Изолированная сессия", "Сброс одним кликом", "README + код"], bullets: ["leonid-ai-engineer-portfolio.onrender.com/sandbox", "leonid-portfolio.onrender.com"], narration: "Начните с интерактивной песочницы: в ней можно пройти все шесть сценариев на синтетических данных без API-ключей. README, eval-отчёт и памятка к собеседованию объясняют устройство проекта и его ограничения. Спасибо за просмотр!"),
]

func color(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat, _ a: CGFloat = 1) -> CGColor {
    CGColor(colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!, components: [r, g, b, a])!
}

func drawText(_ text: String, in rect: CGRect, size: CGFloat, foreground: CGColor, context: CGContext, weight: CTFontSymbolicTraits = []) {
    let name = weight.contains(.traitBold) ? "Arial-BoldMT" : "ArialMT"
    let font = CTFontCreateWithName(name as CFString, size, nil)
    let attrs: [NSAttributedString.Key: Any] = [
        NSAttributedString.Key(kCTFontAttributeName as String): font,
        NSAttributedString.Key(kCTForegroundColorAttributeName as String): foreground
    ]
    let attributed = NSAttributedString(string: text, attributes: attrs)
    let setter = CTFramesetterCreateWithAttributedString(attributed as CFAttributedString)
    let path = CGPath(rect: rect, transform: nil)
    CTFrameDraw(CTFramesetterCreateFrame(setter, CFRange(location: 0, length: attributed.length), path, nil), context)
}

func rounded(_ rect: CGRect, radius: CGFloat, fill: CGColor, context: CGContext, stroke: CGColor? = nil) {
    let path = CGPath(roundedRect: rect, cornerWidth: radius, cornerHeight: radius, transform: nil)
    context.addPath(path); context.setFillColor(fill); context.fillPath()
    if let stroke { context.addPath(path); context.setStrokeColor(stroke); context.setLineWidth(1.5); context.strokePath() }
}

func render(_ scene: Scene, frame: Int64, pool: CVPixelBufferPool, width: Int, height: Int) -> CVPixelBuffer {
    var optionalBuffer: CVPixelBuffer?
    CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, pool, &optionalBuffer)
    let buffer = optionalBuffer!
    CVPixelBufferLockBaseAddress(buffer, [])
    let ctx = CGContext(data: CVPixelBufferGetBaseAddress(buffer), width: width, height: height, bitsPerComponent: 8,
                        bytesPerRow: CVPixelBufferGetBytesPerRow(buffer), space: CGColorSpaceCreateDeviceRGB(),
                        bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue)!
    let t = CGFloat(frame % 600) / 600
    let gradient = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: [color(0.035,0.055,0.105),color(0.075 + t*0.035,0.12,0.22)] as CFArray, locations: [0,1])!
    ctx.drawLinearGradient(gradient, start: CGPoint(x: 0,y: 0), end: CGPoint(x: width,y: height), options: [])
    ctx.setFillColor(color(0.32,0.88,0.73,0.08)); ctx.fillEllipse(in: CGRect(x: 930,y: 460,width: 500,height: 500))
    drawText("LEONID  /  AI ENGINEER PORTFOLIO", in: CGRect(x: 68,y: 668,width: 700,height: 24), size: 16, foreground: color(0.43,0.91,0.78), context: ctx, weight: .traitBold)
    drawText(scene.eyebrow, in: CGRect(x: 70,y: 589,width: 1120,height: 30), size: 18, foreground: color(0.56,0.68,0.96), context: ctx, weight: .traitBold)
    drawText(scene.title, in: CGRect(x: 68,y: 420,width: 1145,height: 160), size: 52, foreground: color(0.94,0.96,1), context: ctx, weight: .traitBold)
    drawText(scene.description, in: CGRect(x: 72,y: 368,width: 1120,height: 52), size: 22, foreground: color(0.70,0.77,0.87), context: ctx)
    let margin: CGFloat = 72, gap: CGFloat = 15, cardY: CGFloat = 207, cardH: CGFloat = 116
    let cardW = (CGFloat(width)-2*margin-gap*3)/4
    for (i, label) in scene.flow.enumerated() {
        let rect = CGRect(x: margin+CGFloat(i)*(cardW+gap),y: cardY,width: cardW,height: cardH)
        rounded(rect,radius:14,fill:color(0.075,0.12,0.20,0.88),context:ctx,stroke:color(0.18,0.25,0.36))
        drawText(String(format:"%02d",i+1),in:CGRect(x:rect.minX+15,y:rect.maxY-33,width:45,height:22),size:14,foreground:color(0.39,0.90,0.76),context:ctx,weight:.traitBold)
        drawText(label,in:CGRect(x:rect.minX+15,y:rect.minY+22,width:cardW-28,height:58),size:20,foreground:color(0.91,0.94,0.99),context:ctx,weight:.traitBold)
        if i < scene.flow.count-1 {
            ctx.setStrokeColor(color(0.39,0.90,0.76));ctx.setLineWidth(2);ctx.move(to:CGPoint(x:rect.maxX+2,y:cardY+cardH/2));ctx.addLine(to:CGPoint(x:rect.maxX+gap-3,y:cardY+cardH/2));ctx.strokePath()
        }
    }
    for (i, bullet) in scene.bullets.enumerated() {
        ctx.setFillColor(color(0.39,0.90,0.76));ctx.fillEllipse(in:CGRect(x:75,y:142-CGFloat(i)*34,width:8,height:8))
        drawText(bullet,in:CGRect(x:94,y:133-CGFloat(i)*34,width:1120,height:27),size:17,foreground:color(0.69,0.77,0.88),context:ctx)
    }
    drawText("PYTHON  ·  FASTAPI  ·  POSTGRESQL  ·  DOCKER  ·  RAG  ·  EVALS", in:CGRect(x:72,y:29,width:950,height:22),size:14,foreground:color(0.43,0.52,0.66),context:ctx,weight:.traitBold)
    CVPixelBufferUnlockBaseAddress(buffer, [])
    return buffer
}

func makeMovie(outputURL: URL, tempURL: URL, audioDir: URL, fps: Int32 = 24) throws {
    let width=1280,height=720
    let writer=try AVAssetWriter(outputURL:tempURL,fileType:.mov)
    let input=AVAssetWriterInput(mediaType:.video,outputSettings:[AVVideoCodecKey:AVVideoCodecType.h264,AVVideoWidthKey:width,AVVideoHeightKey:height,AVVideoCompressionPropertiesKey:[AVVideoAverageBitRateKey:3_000_000,AVVideoProfileLevelKey:AVVideoProfileLevelH264HighAutoLevel]])
    input.expectsMediaDataInRealTime=false
    let adaptor=AVAssetWriterInputPixelBufferAdaptor(assetWriterInput:input,sourcePixelBufferAttributes:[kCVPixelBufferPixelFormatTypeKey as String:kCVPixelFormatType_32BGRA,kCVPixelBufferWidthKey as String:width,kCVPixelBufferHeightKey as String:height,kCVPixelBufferCGImageCompatibilityKey as String:true,kCVPixelBufferCGBitmapContextCompatibilityKey as String:true])
    writer.add(input);writer.startWriting();writer.startSession(atSourceTime:.zero)
    var cursor:Int64=0
    for (sceneIndex,scene) in scenes.enumerated() {
        let clip=AVURLAsset(url:audioDir.appendingPathComponent(String(format:"scene-%02d.aiff",sceneIndex+1)))
        let duration=clip.duration.seconds
        let count=Int64(ceil(duration*Double(fps)))
        for local in 0..<count {
            while !input.isReadyForMoreMediaData { Thread.sleep(forTimeInterval:0.002) }
            let buffer=render(scene,frame:local,pool:adaptor.pixelBufferPool!,width:width,height:height)
            guard adaptor.append(buffer,withPresentationTime:CMTime(value:cursor+local,timescale:fps)) else { throw writer.error ?? NSError(domain:"tour",code:1) }
        }
        cursor += count
    }
    input.markAsFinished()
    let finished=DispatchSemaphore(value:0);writer.finishWriting{finished.signal()};finished.wait()
    guard writer.status == .completed else { throw writer.error ?? NSError(domain:"tour",code:2) }
    let videoAsset=AVURLAsset(url:tempURL);let composition=AVMutableComposition()
    let videoTrack=composition.addMutableTrack(withMediaType:.video,preferredTrackID:kCMPersistentTrackID_Invalid)!
    let sourceVideo=try videoAsset.tracks(withMediaType:.video).first!
    let videoDuration=videoAsset.duration
    try videoTrack.insertTimeRange(CMTimeRange(start:.zero,duration:videoDuration),of:sourceVideo,at:.zero)
    let audioTrack=composition.addMutableTrack(withMediaType:.audio,preferredTrackID:kCMPersistentTrackID_Invalid)!
    var audioCursor=CMTime.zero
    for sceneIndex in scenes.indices {
        let clip=AVURLAsset(url:audioDir.appendingPathComponent(String(format:"scene-%02d.aiff",sceneIndex+1)))
        guard let source=try clip.tracks(withMediaType:.audio).first else { continue }
        try audioTrack.insertTimeRange(CMTimeRange(start:.zero,duration:clip.duration),of:source,at:audioCursor)
        audioCursor = CMTimeAdd(audioCursor,CMTime(value:Int64(ceil(clip.duration.seconds*Double(fps))),timescale:fps))
    }
    guard let exporter=AVAssetExportSession(asset:composition,presetName:AVAssetExportPresetHighestQuality) else { throw NSError(domain:"tour",code:3) }
    exporter.outputURL = outputURL;exporter.outputFileType = .mp4;exporter.shouldOptimizeForNetworkUse = true
    let exported=DispatchSemaphore(value:0);exporter.exportAsynchronously{exported.signal()};exported.wait()
    guard exporter.status == .completed else { throw exporter.error ?? NSError(domain:"tour",code:4) }
}

func runSay(_ text:String,output:URL) throws {
    let task=Process();task.executableURL=URL(fileURLWithPath:"/usr/bin/say");task.arguments=["-v","Milena","-r","178","-o",output.path,text]
    try task.run();task.waitUntilExit();if task.terminationStatus != 0 { throw NSError(domain:"say",code:Int(task.terminationStatus)) }
}

func srtTime(_ frame:Int64,fps:Int64)->String {
    let ms=frame*1000/fps;let hours=ms/3_600_000;let minutes=(ms/60_000)%60;let seconds=(ms/1000)%60;let millis=ms%1000
    return String(format:"%02lld:%02lld:%02lld,%03lld",hours,minutes,seconds,millis)
}

func writeCaptions(directory:URL,output:URL,fps:Int64=24) throws {
    var cues:[String]=[];var cursor:Int64=0;var index=1
    for (sceneIndex, scene) in scenes.enumerated() {
        let asset=AVURLAsset(url:directory.appendingPathComponent(String(format:"scene-%02d.aiff",sceneIndex+1)))
        let durationFrames=Int64(ceil(asset.duration.seconds*Double(fps)))
        let sentences=scene.narration.split(whereSeparator:{".!?".contains($0)}).map(String.init).filter{ !$0.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty }
        let weights=sentences.map{max(1,$0.count)};let total=weights.reduce(0,+);var local:Int64=0
        for (sentence,weight) in zip(sentences,weights) {
            let length=max(1,durationFrames*Int64(weight)/Int64(max(1,total)))
            let end=min(cursor+durationFrames,cursor+local+length)
            cues.append("\(index)\n\(srtTime(cursor+local,fps:fps)) --> \(srtTime(end,fps:fps))\n\(sentence.trimmingCharacters(in:.whitespacesAndNewlines)).\n")
            local += length;index += 1
        }
        cursor += durationFrames
    }
    let captionURL=output.deletingPathExtension().appendingPathExtension("srt")
    try cues.joined(separator:"\n").write(to:captionURL,atomically:true,encoding:.utf8)
}

do {
    guard CommandLine.arguments.count == 2 else { fatalError("Usage: swift create_ai_portfolio_tour.swift /absolute/path/to/output.mp4") }
    let output=URL(fileURLWithPath:CommandLine.arguments[1]);try FileManager.default.createDirectory(at:output.deletingLastPathComponent(),withIntermediateDirectories:true);try? FileManager.default.removeItem(at:output);try? FileManager.default.removeItem(at:output.deletingPathExtension().appendingPathExtension("srt"))
    let temp=FileManager.default.temporaryDirectory.appendingPathComponent("ai-portfolio-tour-\(UUID().uuidString)",isDirectory:true)
    try FileManager.default.createDirectory(at:temp,withIntermediateDirectories:true)
    for (index,scene) in scenes.enumerated(){try runSay(scene.narration,output:temp.appendingPathComponent(String(format:"scene-%02d.aiff",index+1)))}
    try makeMovie(outputURL:output,tempURL:temp.appendingPathComponent("visual.mov"),audioDir:temp)
    try writeCaptions(directory:temp,output:output)
    try? FileManager.default.removeItem(at:temp)
    print("Wrote \(output.path)")
} catch { fputs("Video creation failed: \(error)\n",stderr);exit(1) }
