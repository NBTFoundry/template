// SPDX-License-Identifier: MPL-2.0
/* My App: the least an NBT Manager application does, on the NBT App SDK. It
 * opens the window, shows its name, sends its heartbeat and status, follows
 * its settings and stops when asked or on a long BACK hold. Keep the order of
 * main(); put the application where the comments say. */
#include <string.h>
#include <unistd.h>

#include <GLES2/gl2.h>

#include "nbt/app/back_gesture.hpp"
#include "nbt/app/clock.hpp"
#include "nbt/app/lifecycle.hpp"
#include "nbt/app/log.hpp"
#include "nbt/app/video.hpp"
#include "nbt/controller/input.hpp"
#include "nbt/frontend/overlay.hpp"

namespace {

const uint32_t kFrameMs = 16;
/* The panel's size, for a health check: it has no window. */
const int kPanelWidth = 1280, kPanelHeight = 480;

struct Input {
  nbt::app::BackGesture back;
  uint64_t now;
};

/* The iDrive controller: state.keys are the NBT_CONTROLLER_* keys held,
 * event.pressed and event.released those that changed, event.rotation the
 * knob's detents (clockwise positive). */
void on_controller(void* context, const nbt_controller_wire_state& state,
                   const nbt::controller::Event& event) {
  Input* in = static_cast<Input*>(context);
  (void)event;
  in->back.update((state.keys & NBT_CONTROLLER_BACK) != 0, in->now);
}

void apply_settings(const nbt::app::Lifecycle& lifecycle) {
  nbt::app::log_set_debug(!strcmp(lifecycle.settings().get("debug_log", "off"), "on"));
}

}  // namespace

int main(int argc, char** argv) {
  /* 1. The bridge: NBT Manager's descriptors, the launch mode, the settings. */
  nbt::app::log_init("myapp");
  nbt::app::Lifecycle lifecycle;
  const int started = lifecycle.init(argc, argv);
  if (started != 0) return started;
  nbt::app::log_install_crash_handlers();
  apply_settings(lifecycle);

  /* 2. The window, on a user launch only: a health check (after an install
   * or an update) has no screen and no input. */
  nbt::app::VideoEgl video;
  nbt::frontend::Overlay overlay;
  const bool user = lifecycle.is_user_mode();
  if (user) {
    const nbt::app::VideoConfig window = {"My App", kPanelWidth, kPanelHeight};
    if (!video.init(lifecycle.surface_id(), &window) || !overlay.init()) {
      nbt::app::log_info("no window: the car will not show it");
      return 1;
    }
  }
  const int width = user ? video.window_width() : kPanelWidth;
  const int height = user ? video.window_height() : kPanelHeight;

  /* 3. Load here what the application needs, also in a health check, so the
   * check covers it; then ready, within 5 seconds of the start. */
  nbt::app::log_info("ready, %dx%d, caps %s", width, height, lifecycle.bridge_caps());
  if (!lifecycle.send_ready()) return 1;

  /* 4. The loop, once per frame: input, the application, the heartbeat with
   * the status line and the settings, the frame. */
  nbt::controller::Input controller;
  Input input;
  while (!lifecycle.stopping()) {
    const uint64_t now = nbt::app::monotonic_ms();
    input.now = now;
    if (lifecycle.controller_fd() >= 0) {
      controller.poll(lifecycle.controller_fd(), &on_controller, &input);
    }
    if (input.back.poll(now) == nbt::app::BackGesture::kLongHold) {
      nbt::app::log_info("BACK held: closing");
      lifecycle.request_stop();
    }
    nbt::app::HostEvent event;
    while (user && video.poll_event(&event)) { /* the desktop build's window */
      const bool escape =
          event.type == nbt::app::HostEvent::kKeyDown && event.key == nbt::app::kHostKeyEscape;
      if (escape || event.type == nbt::app::HostEvent::kClose) lifecycle.request_stop();
    }

    bool changed = false;
    lifecycle.tick(now, "Running", &changed); /* the status: at most 24 characters */
    if (changed) apply_settings(lifecycle);
    (void)lifecycle.consume_show_requested();

    if (user) {
      glViewport(0, 0, width, height);
      glClearColor(0.05f, 0.07f, 0.09f, 1.0f);
      glClear(GL_COLOR_BUFFER_BIT);
      const int scale = nbt::frontend::Overlay::scale_for(height) * 2;
      overlay.begin(width, height);
      overlay.text((width - nbt::frontend::Overlay::text_width("My App", scale)) / 2,
                   (height - nbt::frontend::Overlay::kGlyph * scale) / 2, scale, "My App",
                   0xffffffffu);
      overlay.end();
      video.swap();
    }
    const uint64_t spent = nbt::app::monotonic_ms() - now;
    usleep(static_cast<useconds_t>((spent < kFrameMs ? kFrameMs - spent : 1) * 1000));
  }

  /* 5. A clean end: status 0 when asked to stop. */
  overlay.shutdown();
  video.shutdown();
  lifecycle.close_fds();
  return 0;
}
