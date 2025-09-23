import { render, screen } from '@testing-library/react'
import { RecCard } from '../components/RecCard'

const rec = {
  id: '1',
  title: 'Cozy Mysteries',
  year: 2020,
  rationale: 'Matches your cozy picks',
  where_to_watch: [{ platform: 'Stan', offer_type: 'stream' }],
  warnings: ['language'],
  flags: ['clever dialogue'],
  prediction: { label: 'ACCEPTABLE', c: 0.7, n: 0.3 },
}

it('renders warnings first then flags', () => {
  render(<RecCard rec={rec as any} />)
  const warnings = screen.getByTestId('warnings')
  const flags = screen.getByTestId('flags')
  expect(warnings).toBeInTheDocument()
  expect(flags).toBeInTheDocument()
})

