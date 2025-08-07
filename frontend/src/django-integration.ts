import { mountEnhancedComponent } from './components/DjangoIntegration';

// Make the mount function available globally for Django templates
declare global {
  interface Window {
    GMAReact: {
      mountComponent: typeof mountEnhancedComponent;
    };
  }
}

window.GMAReact = {
  mountComponent: mountEnhancedComponent,
};

// Auto-mount components based on data attributes
document.addEventListener('DOMContentLoaded', () => {
  const reactElements = document.querySelectorAll('[data-react-component]');

  reactElements.forEach((element) => {
    const componentName = element.getAttribute('data-react-component');
    const propsData = element.getAttribute('data-react-props');

    if (componentName && element.id) {
      let props = {};
      if (propsData) {
        try {
          props = JSON.parse(propsData);
        } catch (error) {
          console.error('Failed to parse React component props:', error);
        }
      }

      mountEnhancedComponent(componentName, element.id, props);
    }
  });
});
