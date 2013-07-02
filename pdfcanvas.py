import tempfile, os

from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

class PDFCanvas:

	def __init__(self, cardw, cardh, outfile, pagesize, margin):
		self.outfile = outfile
		self.drawbackground = True
		self.pagesize = pagesize
		self.x = 0
		self.y = 0
		self.cardw = cardw
		self.cardh = cardh
		self.columns = int((pagesize[0]-margin[0]*2) / self.cardw)
		self.rows = int((pagesize[1]-margin[1]*2) / self.cardh)
		self.offsetx = (pagesize[0] - self.columns*self.cardw) * 0.5
		self.offsety = (pagesize[1] - self.cardh) - (pagesize[1] - self.rows*self.cardh) * 0.5
		self.tempfile = tempfile.mktemp()
		self.canvas = canvas.Canvas(self.tempfile, pagesize=(pagesize[0], pagesize[1]))
		self.styles = {}
		self.page = False
		self.notefmt = None
		self.guides = False

	def drawImage(self, filename, x, y, width, height):
		if os.path.exists(filename):
			self.canvas.drawImage(filename, x, y, width, height)

	def addStyle(self, data):
		name = data.get('name', "")
		s = ParagraphStyle(name)
		fontfile = data.get('font', "Helvetica")
		if fontfile.endswith(".ttf") or fontfile.endswith(".otf"):
			fontname = os.path.splitext(fontfile)[0]
			pdfmetrics.registerFont(TTFont(fontname, fontfile))
			s.fontName = fontname
		else:
			s.fontName = fontfile
		s.fontSize = data.get('size', 10)
		s.alignment = dict(center=TA_CENTER, left=TA_LEFT, right=TA_RIGHT)[data.get('align', 'left')]
		s.leading = data.get('leading', s.leading)
		self.styles[name] = s

	def renderText(self, text, stylename, x, y, width, height):
		lines = text.splitlines()
		i = 0
		style = self.styles[stylename]
		for l in lines:
			p = Paragraph(l, style)
			tx, ty = p.wrap(width, height)
			voffset = ty*0.5*len(lines) - ty*i
			p.drawOn(self.canvas, x, y - voffset)
			i += 1

	def beginCard(self, card):
		if not self.page:
			self.beginPage()
		self.canvas.saveState()
		self.canvas.translate(self.offsetx + self.x*self.cardw, self.offsety - self.y*self.cardh)

	def endCard(self):
		self.canvas.restoreState()
		# advance the card position
		self.x += 1
		if self.x >= self.columns:
			self.x = 0
			self.y += 1
			if self.y >= self.rows:
				self.endPage()

	def beginPage(self):
		assert not self.page
		if self.drawbackground:
			# render background
			self.canvas.setFillColorRGB(0, 0, 0)
			self.canvas.rect(0, 0, self.pagesize[0], self.pagesize[1], stroke=0, fill=1)
		self.page = True

	def endPage(self):
		assert self.page
		if self.notefmt: 
			self.note()
		if self.guides:
			self.drawGuides()
		self.x = 0
		self.y = 0
		self.canvas.showPage()
		self.page = False

	def drawGuides(self):
		GUIDECOLOR = (0.5, 0.5, 0.5)
		canvas = self.canvas
		left = self.offsetx
		right = left + self.cardw*self.columns
		top = self.offsety + self.cardh
		bottom = top - self.cardh*self.rows
		for ix in range(0, self.columns+1):
			x = self.offsetx + self.cardw*ix
			canvas.setStrokeColorRGB(*GUIDECOLOR)
			canvas.line(x, self.pagesize[1], x, top)
			canvas.line(x, bottom, x, 0)
			canvas.setStrokeColorRGB(1, 1, 1)
			canvas.line(x, top, x, bottom)
		for iy in range(-1, self.rows):
			y = self.offsety - self.cardh*iy
			canvas.setStrokeColorRGB(*GUIDECOLOR)
			canvas.line(0, y, left, y)
			canvas.line(right, y, self.pagesize[0], y)
			canvas.setStrokeColorRGB(1, 1, 1)
			canvas.line(left, y, right, y) 

	def finish(self):
		if self.page:
			self.endPage()
		self.canvas.save()
		outfile = self.outfile
		fn, ext = os.path.splitext(outfile)
		amt = 0
		while True:
			try:
				if os.path.exists(outfile):
					os.unlink(outfile)
				os.rename(self.tempfile, outfile)
				return
			except WindowsError as e:
				amt += 1
				outfile = "{0}_{1}{2}".format(fn, amt, ext)