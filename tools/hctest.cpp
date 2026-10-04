// Load a hyprcursor theme the way Hyprland does and report load time and per-shape frames.
// usage: hctest <theme> <size> [shape...]
#include <hyprcursor/hyprcursor.hpp>
#include <cairo/cairo.h>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include <algorithm>
#include <fstream>
static long rssKb() { std::ifstream f("/proc/self/status"); std::string l; while (std::getline(f, l)) if (l.rfind("VmRSS:", 0) == 0) return std::stol(l.substr(6)); return -1; }

int main(int argc, char** argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s <theme> <size> [shape...]\n", argv[0]);
        return 2;
    }
    using clk = std::chrono::steady_clock;
    Hyprcursor::SManagerOptions opts;
    opts.allowDefaultFallback = false;
    opts.logFn                = [](enum eHyprcursorLogLevel lvl, char* msg) {
        if (lvl >= HC_LOG_WARN)
            fprintf(stderr, "hyprcursor: %s\n", msg);
    };
    printf("rss start %ld kB\n", rssKb());
    auto t0 = clk::now();
    Hyprcursor::CHyprcursorManager mgr(argv[1], opts);
    if (!mgr.valid()) {
        printf("INVALID theme %s\n", argv[1]);
        return 1;
    }
    Hyprcursor::SCursorStyleInfo style{.size = (unsigned)atoi(argv[2])};
    auto t1 = clk::now();
    if (!mgr.loadThemeStyle(style)) {
        printf("loadThemeStyle failed\n");
        return 1;
    }
    auto t2 = clk::now();
    printf("open %.1f ms, loadThemeStyle(%u) %.1f ms\n", std::chrono::duration<double, std::milli>(t1 - t0).count(), style.size,
           std::chrono::duration<double, std::milli>(t2 - t1).count());
    printf("rss after load %ld kB\n", rssKb());
    int bad = 0;
    for (int i = 3; i < argc; ++i) {
        auto shape = mgr.getShape(argv[i], style);
        if (shape.images.empty()) {
            printf("MISSING %s\n", argv[i]);
            bad++;
            continue;
        }
        long total = 0;
        for (auto& im : shape.images)
            total += im.delay;
        // coverage of frame 0: alpha sum and bounding box of pixels with alpha > 32
        auto& im = shape.images[0];
        cairo_surface_flush(im.surface);
        const int      w = cairo_image_surface_get_width(im.surface), h = cairo_image_surface_get_height(im.surface);
        const int      stride = cairo_image_surface_get_stride(im.surface);
        unsigned char* px     = cairo_image_surface_get_data(im.surface);
        long           alpha  = 0;
        int            minx = w, miny = h, maxx = -1, maxy = -1;
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                const unsigned a = px[y * stride + x * 4 + 3];
                alpha += a;
                if (a > 32) {
                    minx = std::min(minx, x), miny = std::min(miny, y);
                    maxx = std::max(maxx, x), maxy = std::max(maxy, y);
                }
            }
        }
        printf("%s frames=%zu size=%d delay0=%d cycle=%ld hot=%d,%d alpha=%ld bbox=%d,%d-%d,%d\n", argv[i], shape.images.size(), im.size, im.delay, total,
               im.hotspotX, im.hotspotY, alpha / 255, minx, miny, maxx, maxy);
    }
    mgr.cursorSurfaceStyleDone(style);
    return bad ? 1 : 0;
}
