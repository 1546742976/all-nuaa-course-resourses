Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.DataWriter, Windows.Storage.Streams, ContentType=WindowsRuntime] | Out-Null
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, $type) { $t=$asTask.MakeGenericMethod($type).Invoke($null,@($op)); $t.GetAwaiter().GetResult() }
[Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime] | Out-Null
$lang = New-Object Windows.Globalization.Language('zh-Hans-CN')
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
Get-ChildItem -LiteralPath '资料\机械工程\机械设计基础\附件\识别临时' -Filter '*.png' | ForEach-Object {
 $stream=New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
 $writer=New-Object Windows.Storage.Streams.DataWriter($stream.GetOutputStreamAt(0)); $writer.WriteBytes([IO.File]::ReadAllBytes($_.FullName)); $null=Await ($writer.StoreAsync()) ([uint32]); $stream.Seek(0)
 $decoder=Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
 $bitmap=Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
 $result=Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
 [IO.File]::WriteAllText([IO.Path]::ChangeExtension($_.FullName,'.txt'), (($result.Lines | ForEach-Object {$_.Text}) -join "`n"), [Text.Encoding]::UTF8)
 $stream.Dispose(); $bitmap.Dispose()
}
