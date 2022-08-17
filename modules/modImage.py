import numpy


def getAverageColor(img):
    """ Returns the average colour used as the image border """
    pix = numpy.array(img)
    border = [[], [], []]

    # North border
    for pixel in pix[0]:
        for i in range(3):
            border[i].append(pixel[i])

    # South border
    for pixel in pix[-1]:
        for i in range(3):
            border[i].append(pixel[i])

    # West and East border
    for j in range(img.height):
        for i in range(3):
            border[i].append(pix[j][0][i])
            border[i].append(pix[j][-1][i])

    return tuple([max(set(color), key=color.count) for color in border])


def getCentralCoordinates(img, t):
    """ Returns coordinates of central image """
    # Find coordinates of main image
    average = getAverageColor(img)
    pix = numpy.array(img)
    n, s, w, e = None, None, None, None

    # North line
    for y in range(img.height):
        for pixel in pix[y]:
            if tuple(pixel) != average:
                n = y - t
                break
        if n:
            break

    if not n:
        n = img.height // 2 - t
    elif n < 0:
        n = 0

    # South line
    for y in reversed(range(img.height)):
        for pixel in pix[y]:
            if tuple(pixel) != average:
                s = y + t
                break
        if s:
            break

    if not s:
        n = img.height // 2 + t
    elif s > img.height - 1:
        n = img.height - 1

    # West line
    for x in range(img.width):
        for y in range(img.height):
            if tuple(pix[y][x]) != average:
                w = x - t
                break
        if w:
            break

    if not w:
        w = img.width // 2 - t
    elif w < 0:
        w = 0

    # East line
    for x in reversed(range(img.width)):
        for y in range(img.height):
            if tuple(pix[y][x]) != average:
                e = x + t
                break
        if e:
            break

    if not e:
        e = img.width // 2 + t
    elif e > img.width - 1:
        e = img.width - 1

    return n, s, w, e
