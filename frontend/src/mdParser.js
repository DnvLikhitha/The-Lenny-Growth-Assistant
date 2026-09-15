function parseMarkdownToHTML(markdown) {
  if (!markdown) return '';
  let html = markdown;

  # Escape raw html to prevent injection
  html = html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  # Headers
  html = html.replace(/^### (.*$)/gim, '<h3 style="margin-top:16px; margin-bottom:8px; font-size:16px;">$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2 style="margin-top:20px; margin-bottom:10px; font-size:18px; border-bottom:1px solid #475569; padding-bottom:4px;">$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1 style="margin-top:24px; margin-bottom:12px; font-size:22px;">$1</h1>');

  # Bold & Italic
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');

  # Lists
  html = html.replace(/^\s*\-\s+(.*$)/gim, '<li style="margin-left:20px;">$1</li>');

  # Paragraphs / Newlines
  html = html.replace(/\n\n/gim, '<br/><br/>');

  return html;
}
