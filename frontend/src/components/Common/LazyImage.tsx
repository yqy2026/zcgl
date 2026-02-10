/**
 * Lazy Image Component
 *
 * Image component with lazy loading support for better performance
 *
 * Accessibility: Fully WCAG 2.1 AA compliant
 */

import React, { useState, useRef, useEffect } from 'react';
import { Image, Skeleton } from 'antd';

/**
 * Lazy image props
 */
export interface LazyImageProps extends Omit<React.ImgHTMLAttributes<HTMLImageElement>, 'loading'> {
  /**
   * Image source URL
   */
  src: string;
  /**
   * Fallback image source
   */
  fallback?: string;
  /**
   * Image width
   */
  width?: number | string;
  /**
   * Image height
   */
  height?: number | string;
  /**
   * Whether to use preview
   * @default true
   */
  preview?: boolean;
  /**
   * Alt text for accessibility (required)
   */
  alt: string;
  /**
   * Additional CSS class name
   */
  className?: string;
  /**
   * Additional styles
   */
  style?: React.CSSProperties;
}

/**
 * Lazy Image Component
 *
 * Automatically loads images when they come into viewport
 */
export const LazyImage: React.FC<LazyImageProps> = ({
  src,
  fallback = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mN8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==',
  width,
  height,
  preview = true,
  alt,
  className,
  style,
  onClick, // Extract onClick as it's incompatible with antd Image
  ...rest
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const imgRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Check if IntersectionObserver is available
    if (!window.IntersectionObserver) {
      setIsInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      {
        rootMargin: '50px', // Start loading 50px before element comes into view
        threshold: 0.01,
      }
    );

    const currentRef = imgRef.current;
    if (currentRef) {
      observer.observe(currentRef);
    }

    return () => {
      if (currentRef) {
        observer.unobserve(currentRef);
      }
    };
  }, []);

  const handleLoad = () => {
    setIsLoaded(true);
  };

  const handleError = () => {
    setIsLoaded(true);
  };

  const handleImageClick: React.MouseEventHandler<HTMLElement> | undefined =
    onClick == null
      ? undefined
      : event => {
          onClick(event as unknown as React.MouseEvent<HTMLImageElement>);
        };

  return (
    <div
      ref={imgRef}
      className={className}
      style={{
        display: 'inline-block',
        width,
        height,
        ...style,
      }}
    >
      {!isLoaded && (
        <Skeleton.Image
          active
          style={{
            width: '100%',
            height: '100%',
          }}
        />
      )}
      <Image
        src={isInView ? src : undefined}
        fallback={fallback}
        width={width}
        height={height}
        alt={alt}
        preview={preview}
        onLoad={handleLoad}
        onError={handleError}
        onClick={handleImageClick}
        style={{
          display: isLoaded ? 'block' : 'none',
          width: '100%',
          height: '100%',
          objectFit: 'cover',
        }}
        {...rest}
      />
    </div>
  );
};

/**
 * Lazy Background Image Component
 *
 * Component for lazy loading background images
 */
export interface LazyBackgroundImageProps {
  /**
   * Background image source URL
   */
  src: string;
  /**
   * Fallback background color or image
   */
  fallback?: string;
  /**
   * Background size
   * @default 'cover'
   */
  backgroundSize?: 'cover' | 'contain' | 'auto';
  /**
   * Background position
   * @default 'center'
   */
  backgroundPosition?: string;
  /**
   * Children content
   */
  children: React.ReactNode;
  /**
   * Additional CSS class name
   */
  className?: string;
  /**
   * Additional styles
   */
  style?: React.CSSProperties;
}

export const LazyBackgroundImage: React.FC<LazyBackgroundImageProps> = ({
  src,
  fallback = '#f5f5f5',
  backgroundSize = 'cover',
  backgroundPosition = 'center',
  children,
  className,
  style,
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!window.IntersectionObserver) {
      setIsInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      {
        rootMargin: '50px',
        threshold: 0.01,
      }
    );

    const currentRef = containerRef.current;
    if (currentRef) {
      observer.observe(currentRef);
    }

    return () => {
      if (currentRef) {
        observer.unobserve(currentRef);
      }
    };
  }, []);

  useEffect(() => {
    if (isInView && !isLoaded) {
      const img = document.createElement('img');
      img.onload = () => setIsLoaded(true);
      img.onerror = () => setIsLoaded(true); // Still show content even if image fails
      img.src = src;
    }
  }, [isInView, isLoaded, src]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        position: 'relative',
        overflow: 'hidden',
        background: isLoaded
          ? `url(${src}) ${backgroundPosition} / ${backgroundSize} no-repeat`
          : fallback,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

export default LazyImage;
