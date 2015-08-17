#!/usr/bin/python
'''
Extracts one or more characters from each of the svg fonts in the SVG directory
and packages them into a 'chars.html' output file.
'''
import math
import os
import svg.path
import sys

SCALE = 0.2
SVG_DIR = 'derived'
TRANSFORM = 'scale({0:.2g}, -{0:0.2g}) translate(0, -900)'.format(SCALE)

# Constants controlling our stroke extraction algorithm.
MIN_CROSSING_ANGLE = 0.1*math.pi
MAX_CROSSING_DISTANCE = 64


def augment_glyph(glyph):
  path = svg.path.parse_path(get_svg_path_data(glyph))
  path = svg.path.Path(
      *[element for element in path if element.start != element.end])
  assert path, 'Got empty path for glyph:\n{0}'.format(glyph)
  paths = break_path(path)
  cusps = get_cusps(paths)
  # Actually augment the glyph. For now, we just mark all detected cusps.
  result = []
  for (i, j, point) in cusps:
    result.append(
        '<circle cx="{0}" cy="{1}" r="4" fill="red" stroke="red"/>'.format(
            int(point.real), int(point.imag)))
  return result

def break_path(path):
  subpaths = [[path[0]]]
  for element in path[1:]:
    if element.start != subpaths[-1][-1].end:
      subpaths.append([])
    subpaths[-1].append(element)
  return [svg.path.Path(*subpath) for subpath in subpaths]

def get_angle(path, index):
  segment1 = path[index]
  tangent1 = segment1.end - segment1.start
  if (type(segment1) == svg.path.QuadraticBezier and
      segment1.end != segment1.control):
    tangent1 = segment1.end - segment1.control
  segment2 = path[(index + 1) % len(path)]
  tangent2 = segment2.end - segment2.start
  if (type(segment2) == svg.path.QuadraticBezier and
      segment2.control != segment2.end):
    tangent2 = segment2.control - segment2.start
  assert tangent1 and tangent2, 'Computing angle for trivial segment!'
  ratio = tangent1/tangent2
  return math.atan2(ratio.imag, ratio.real)

def get_cusps(paths):
  result = []
  for i, path in enumerate(paths):
    for j, element in enumerate(path):
      if abs(get_angle(path, j)) > MIN_CROSSING_ANGLE:
        result.append((i, j, element.end))
  return result

def get_svg_path_data(glyph):
  left = ' d="'
  start = max(glyph.find(left), glyph.find(left.replace(' ', '\n')))
  assert start >= 0, 'Glyph missing d=".*" block:\n{0}'.format(repr(glyph))
  end = glyph.find('"', start + len(left))
  assert end >= 0, 'Glyph missing d=".*" block:\n{0}'.format(repr(glyph))
  return glyph[start + len(left):end].replace('\n', ' ')


if __name__ == '__main__':
  assert len(sys.argv) > 1, 'Usage: ./getchar.py <unicode_codepoint>+'
  svgs = [file_name for file_name in os.listdir(SVG_DIR)
          if file_name.endswith('.svg') and not file_name.startswith('.')]
  glyphs = []
  for file_name in svgs:
    glyphs.append([])
    with open(os.path.join(SVG_DIR, file_name)) as file:
      data = file.read()
    for codepoint in sys.argv[1:]:
      index = data.find('unicode="&#x{0};"'.format(codepoint))
      if index < 0:
        print >> sys.stderr, '{0}: missing {1}'.format(file_name, codepoint)
        continue
      (left, right) = ('<glyph', '/>')
      (start, end) = (data.rfind(left, 0, index), data.find(right, index))
      if start < 0 or end < 0:
        print >> sys.stderr, '{0}: malformed {1}'.format(file_name, codepoint)
        continue
      glyphs[-1].append(data[start:end + len(right)])

  with open('chars.html', 'w') as f:
    f.write('<!DOCTYPE html>\n  <html>\n    <body>\n')
    for row in glyphs:
      f.write('      <div>\n')
      for glyph in row:
        size = int(1024*SCALE)
        f.write('        <svg width="{0}" height="{0}">\n'.format(size))
        f.write('          <g transform="{0}">\n'.format(TRANSFORM))
        f.write(glyph.replace('<glyph', '<path'))
        for extra in augment_glyph(glyph):
          f.write(extra)
        f.write('          </g>\n')
        f.write('        </svg>\n')
      f.write('      </div>\n')
    f.write('    </body>\n  </html>')
