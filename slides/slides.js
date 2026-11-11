const slides = Array.from(document.querySelectorAll(".slide"));
const controls = document.querySelector(".controls");
const previous = document.querySelector("#previous");
const next = document.querySelector("#next");
const position = document.querySelector("#position");
const progress = document.querySelector("progress");

let current = 0;

function showSlide(focusHeading = false) {
  const id = location.hash.slice(1);
  const requested = slides.findIndex((slide) => slide.id === id);
  current = Math.max(0, requested);

  slides.forEach((slide, index) => {
    slide.hidden = index !== current;
  });
  previous.disabled = current === 0;
  next.disabled = current === slides.length - 1;
  position.textContent = `${current + 1} / ${slides.length}`;
  progress.value = current + 1;

  if (focusHeading) {
    window.scrollTo(0, 0);
    slides[current].querySelector("h1, h2").focus({ preventScroll: true });
  }
}

function goTo(index) {
  if (index < 0 || index >= slides.length || index === current) return;
  location.hash = slides[index].id;
}

previous.addEventListener("click", () => goTo(current - 1));
next.addEventListener("click", () => goTo(current + 1));
window.addEventListener("hashchange", () => showSlide(true));

document.addEventListener("keydown", (event) => {
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.defaultPrevented) return;

  const destinations = {
    ArrowLeft: current - 1,
    ArrowRight: current + 1,
    Home: 0,
    End: slides.length - 1,
  };

  if (Object.hasOwn(destinations, event.key)) {
    event.preventDefault();
    goTo(destinations[event.key]);
  }
});

progress.max = slides.length;
showSlide(Boolean(location.hash));
controls.hidden = false;
