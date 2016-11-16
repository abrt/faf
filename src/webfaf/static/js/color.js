function getColors(neededColors){
    if (typeof neededColors === 'undefined'){
        neededColors = 1;
    }

    var colorPool = ["#edc240", "#afd8f8", "#cb4b4b", "#4da74d", "#9440ed"];
    var c, colors = [],
            colorPoolSize = colorPool.length, variation = 0;

    for (i = 0; i < neededColors; i++) {

        c = $.color.parse(colorPool[i % colorPoolSize] || "#666");

        // Each time we exhaust the colors in the pool we adjust
        // a scaling factor used to produce more variations on
        // those colors. The factor alternates negative/positive
        // to produce lighter/darker colors.

        // Reset the variation after every few cycles, or else
        // it will end up producing only white or black colors.

        if (i % colorPoolSize == 0 && i) {
            if (variation >= 0) {
                if (variation < 0.5) {
                    variation = -variation - 0.2;
                } else variation = 0;
            } else variation = -variation;
        }

        colors[i] = c.scale('rgb', 1 + variation);
    }
    return colors;
}

function LightenDarkenColor(col, amt) {

    var usePound = false;

    if (col[0] == "#") {
        col = col.slice(1);
        usePound = true;
    }

    var num = parseInt(col,16);

    var r = (num >> 16) + amt;

    if (r > 255) r = 255;
    else if  (r < 0) r = 0;

    var b = ((num >> 8) & 0x00FF) + amt;

    if (b > 255) b = 255;
    else if  (b < 0) b = 0;

    var g = (num & 0x0000FF) + amt;

    if (g > 255) g = 255;
    else if (g < 0) g = 0;

    return (usePound?"#":"") + String("000000" + (g | (b << 8) | (r << 16)).toString(16)).slice(-6);

}

function componentToHex(c) {
    var hex = c.toString(16);
    return hex.length == 1 ? "0" + hex : hex;
}

function rgbToHex(r, g, b) {
    return "#" + componentToHex(r) + componentToHex(g) + componentToHex(b);
}
