// Mount React islands declared in ERB via data-react-component attributes.
//
// Usage in ERB:
//   <div data-react-component="ItemCard"
//        data-props='<%= { kind: item.kind, tone: item.tone, name: item.name }.to_json %>'>
//   </div>
//
// To add a new component: import it below and add it to the COMPONENTS map.
import ReactDOM from "react-dom";
import { ItemCard } from "almirah/item-card";

const COMPONENTS = {
  ItemCard,
};

function mountAll() {
  document.querySelectorAll("[data-react-component]").forEach(function (el) {
    const name = el.dataset.reactComponent;
    const Component = COMPONENTS[name];
    if (!Component) {
      console.warn("[almirah/mount] Unknown React component:", name);
      return;
    }
    let props = {};
    try {
      props = JSON.parse(el.dataset.props || "{}");
    } catch (e) {
      console.error("[almirah/mount] Could not parse props for", name, e);
    }
    // React 18 createRoot is preferred but requires react-dom/client. The
    // legacy render is fine for these small islands.
    ReactDOM.render(React.createElement(Component, props), el);
  });
}

// Mount on initial load
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mountAll);
} else {
  mountAll();
}

// Re-mount after Turbo page transitions
document.addEventListener("turbo:load", mountAll);

export { mountAll };
