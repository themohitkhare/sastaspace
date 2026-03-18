import React from 'react';
import { render, screen } from '@testing-library/react';
import CardDisplay from './CardDisplay';

const mockCard = {
  card_id: 'test-1',
  identity_id: 'genesis',
  name: 'Genesis',
  types: ['CREATION'],
  rarity: 'COMMON',
  shard_yield: 1,
  content_type: 'STORY',
  text: 'From the silence, something stirred—',
  category: null,
  community_count: 0,
};

describe('CardDisplay', () => {
  it('renders card name', () => {
    render(<CardDisplay card={mockCard} totalCards={10} currentIndex={0} />);
    expect(screen.getByTestId('card-name')).toHaveTextContent('Genesis');
  });

  it('renders card text', () => {
    render(<CardDisplay card={mockCard} totalCards={10} currentIndex={0} />);
    expect(screen.getByTestId('card-text')).toHaveTextContent('From the silence');
  });

  it('renders rarity label', () => {
    render(<CardDisplay card={mockCard} totalCards={10} currentIndex={0} />);
    expect(screen.getByTestId('rarity-label')).toHaveTextContent('COMMON');
  });

  it('renders type badges', () => {
    render(<CardDisplay card={mockCard} totalCards={10} currentIndex={0} />);
    expect(screen.getByTestId('type-badge-CREATION')).toBeInTheDocument();
  });

  it('renders shard yield', () => {
    render(<CardDisplay card={mockCard} totalCards={10} currentIndex={0} />);
    expect(screen.getByTestId('shard-yield')).toHaveTextContent('Yield: 1 shard');
  });

  it('renders card counter', () => {
    render(<CardDisplay card={mockCard} totalCards={10} currentIndex={3} />);
    expect(screen.getByText('4/10')).toBeInTheDocument();
  });

  it('renders resource card differently', () => {
    const resourceCard = { ...mockCard, content_type: 'RESOURCE', text: '' };
    render(<CardDisplay card={resourceCard} totalCards={10} currentIndex={0} />);
    expect(screen.getByTestId('card-text')).toHaveTextContent('+1 shards');
  });

  it('returns null when no card', () => {
    const { container } = render(<CardDisplay card={null} totalCards={10} currentIndex={0} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders multi-type card badges', () => {
    const multiCard = { ...mockCard, types: ['CREATION', 'DESTRUCTION'] };
    render(<CardDisplay card={multiCard} totalCards={10} currentIndex={0} />);
    expect(screen.getByTestId('type-badge-CREATION')).toBeInTheDocument();
    expect(screen.getByTestId('type-badge-DESTRUCTION')).toBeInTheDocument();
  });
});
