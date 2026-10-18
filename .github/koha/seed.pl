#!/usr/bin/perl
# Seeds a koha-testing-docker instance for LibSync's live driver checks
# (.github/workflows/koha-live.yml). Runs inside the Koha container via
# koha-shell. Prints one JSON object for the workflow to read.
#
# - Turns on OAuth2 client credentials and makes an API key for the KTD
#   superlibrarian (koha/koha), as a library would for LibSync's Koha driver.
# - Creates a test patron with a known card and PIN for the SIP2 checks.
# - Checks out one single-copy item to that patron, so availability
#   ("checked out") and the patron's charged count have a known answer.
# Everything here is throwaway test data in a throwaway container.

use Modern::Perl;
use JSON qw( encode_json );
use C4::Context;
use Koha::ApiKey;
use Koha::ApiKeys;
use Koha::Checkout;
use Koha::Checkouts;
use Koha::Items;
use Koha::Patron::Categories;
use Koha::Patrons;
use Koha::DateUtils qw( dt_from_string );

C4::Context->set_preference( 'RESTOAuth2ClientCredentials', 1 );

my $admin = Koha::Patrons->find( { userid => 'koha' } ) or die "No koha superlibrarian\n";
my $key   = Koha::ApiKey->new( { patron_id => $admin->id, description => 'libsync-ci' } )->store;

my $dbh = C4::Context->dbh;
my ($itemnumber) = $dbh->selectrow_array(
    q{SELECT MIN(i.itemnumber) FROM items i JOIN biblio b ON b.biblionumber = i.biblionumber
      WHERE b.title IS NOT NULL AND CHAR_LENGTH(b.title) > 5
        AND i.onloan IS NULL AND i.notforloan = 0 AND i.itemlost = 0 AND i.withdrawn = 0
        AND i.biblionumber IN (SELECT biblionumber FROM items GROUP BY biblionumber HAVING COUNT(*) = 1)}
) or die "No single-copy item in the sample data\n";
my $item   = Koha::Items->find($itemnumber);
my $biblio = $item->biblio;

my $card = 'LIBSYNC0001';
my $pin  = 'Libsync-ci-2026';
my $patron = Koha::Patrons->find( { cardnumber => $card } ) || Koha::Patron->new(
    {
        cardnumber   => $card,
        userid       => 'libsyncci',
        surname      => 'Check',
        firstname    => 'LibSync',
        categorycode => Koha::Patron::Categories->search( { category_type => 'A' } )->next->categorycode,
        branchcode   => $item->homebranch,
        dateexpiry   => dt_from_string->add( years => 1 )->ymd,
    }
)->store;
$patron->set_password( { password => $pin, skip_validation => 1 } );

my $due = dt_from_string->add( days => 14 )->strftime('%Y-%m-%d 23:59:00');
Koha::Checkout->new(
    {
        borrowernumber => $patron->borrowernumber,
        itemnumber     => $item->itemnumber,
        branchcode     => $item->homebranch,
        issuedate      => dt_from_string->strftime('%Y-%m-%d %H:%M:%S'),
        date_due       => $due,
    }
)->store;
$item->onloan( substr( $due, 0, 10 ) )->store;

print encode_json(
    {
        client_id      => $key->client_id,
        client_secret  => $key->plain_text_secret,
        card           => $card,
        pin            => $pin,
        biblio_id      => $biblio->biblionumber,
        title          => $biblio->title,
        branch         => $item->homebranch,
    }
), "\n";
