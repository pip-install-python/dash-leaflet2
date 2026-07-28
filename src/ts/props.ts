import React from 'react';

/**
 * Props that Dash injects into / reads from every component.
 * Concatenate with a component's own props:
 *
 *   type Props = { center?: [number, number] } & DashComponentProps;
 */
export type DashComponentProps = {
    /**
     * The ID used to identify this component in Dash callbacks.
     */
    id?: string;

    /**
     * Dash-assigned callback that should be called to report property changes
     * to Dash, to make them available for callbacks.
     */
    setProps?: (props: Record<string, any>) => void;

    /**
     * Often-used CSS class name(s) for the root element.
     */
    className?: string;

    /**
     * Inline style for the root element. For Map, this is where you set height.
     */
    style?: React.CSSProperties;
};
