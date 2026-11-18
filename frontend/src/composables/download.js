export function downloadText(text, filename, contentType = 'text/csv;charset=utf-8') {
  const body = contentType.startsWith('text/csv') && !text.startsWith('\uFEFF') ? `\uFEFF${text}` : text
  const url = URL.createObjectURL(new Blob([body], { type: contentType }))
  const link = document.createElement('a')
  link.href = url; link.download = filename
  document.body.append(link); link.click(); link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
