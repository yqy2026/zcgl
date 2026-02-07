const getNodeEnv = (): string | undefined => {
  if (typeof process === 'undefined') {
    return undefined;
  }

  const nodeEnv = process.env.NODE_ENV;
  return typeof nodeEnv === 'string' && nodeEnv !== '' ? nodeEnv : undefined;
};

export const getRuntimeMode = (): string => {
  const nodeEnv = getNodeEnv();
  if (nodeEnv === 'development' || nodeEnv === 'production') {
    return nodeEnv;
  }

  const viteMode = import.meta.env.MODE;
  if (typeof viteMode === 'string' && viteMode !== '') {
    return viteMode;
  }

  if (nodeEnv != null) {
    return nodeEnv;
  }

  return import.meta.env.PROD === true ? 'production' : 'development';
};

export const isDevelopmentMode = (): boolean => getRuntimeMode() === 'development';

export const isProductionMode = (): boolean => getRuntimeMode() === 'production';
